"""Fake DNS/HTTP retrieval checks; nothing here contacts an external service."""

import os
import socket
import threading
import time
import unittest
from unittest.mock import patch

from eu_compliance_guard import sources as s

HOST = "eur-lex.europa.eu"
URL = f"https://{HOST}/legal-content/EN/TXT/?uri=FICTIONAL"
PUBLIC = "93.184.216.34"
PAGE = b"<!doctype html><html lang='en'><body>FICTIONAL-001</body></html>"
HTML = [("Content-Type", "text/html; charset=utf-8")]


class FakeResponse:
    def __init__(self, status=200, headers=None, body=b"", chunk_delay=None):
        self.status = status
        self.headers = list(HTML if headers is None else headers)
        self.body, self.chunk_delay, self.closed = body, chunk_delay, False

    def read(self, size):
        if self.chunk_delay:
            self.chunk_delay()
        chunk, self.body = self.body[:size], self.body[size:]
        return chunk

    def close(self):
        self.closed = True


class FakeTransport:
    """Answers by host and URL target; records every resolve and GET it receives."""
    def __init__(self, dns=None, responses=None, errors=None):
        self.dns = dns or {}
        self.responses = responses or {}
        self.errors = errors or {}
        self.calls = []

    def resolve(self, host):
        self.calls.append(("resolve", host))
        return self.dns.get(host, [PUBLIC])

    def get(self, host, address, target, timeout):
        self.calls.append(("get", host, address, target, timeout))
        if address in self.errors:
            raise self.errors[address]
        response = self.responses[(host, target)]
        return response() if callable(response) else response


def fetch(transport, url=URL, *, limit=s.MAX_RESPONSE_BYTES, deadline=None, redirect_hosts=(), **options):
    request = s.TargetRequest("target-example", url, tuple(redirect_hosts))
    return s.fetch(request, transport, limit=limit, deadline=time.monotonic() + 30 if deadline is None else deadline, **options)


def target_of(url):
    return s.check_url(url, s.OFFICIAL_HOSTS)[1]


class UrlAndAddressPolicyTests(unittest.TestCase):
    def test_only_exact_registered_https_hosts_on_port_443(self):
        self.assertEqual(s.check_url(URL, s.OFFICIAL_HOSTS), (HOST, "/legal-content/EN/TXT/?uri=FICTIONAL"))
        self.assertEqual(s.check_url(f"https://{HOST}:443", s.OFFICIAL_HOSTS), (HOST, "/"))
        self.assertEqual(s.check_url(f"https://{HOST}?q=1", s.OFFICIAL_HOSTS), (HOST, "/?q=1"))
        refused = {
            "unsafe-url": [f"http://{HOST}/", f"https://user:pw@{HOST}/", f"https://user@{HOST}/", f"https://{HOST}:8443/",
                           f"https://{HOST}:0/", f"https://{HOST}:x/", f"https://{HOST}/#frag", f"https://{HOST}/a b",
                           f"https://{HOST}/\\a", f"https://{HOST}/\x00", f"https://EUR-LEX.europa.eu/",
                           "https://127.0.0.1/", "https://[::1]/", f"https://{HOST}%2f@evil.example/",
                           f"https://{HOST}/" + "a" * 4096, f"https://{HOST}/é", f"ftp://{HOST}/", "//" + HOST],
            "host-not-official": ["https://example.invalid/", "https://evil.europa.eu/", f"https://{HOST}.evil.example/",
                                  "https://europa.eu/", "https://edpb.europa.eu/"],
        }
        for code, urls in refused.items():
            for url in urls:
                with self.subTest(url=url), self.assertRaises(s.RetrievalFailure) as caught:
                    s.check_url(url, s.OFFICIAL_HOSTS)
                self.assertEqual(caught.exception.code, code)

    def test_redirect_hosts_must_be_in_registry(self):
        request = s.TargetRequest("t", URL, ("www.edpb.europa.eu",))
        self.assertEqual(s.allowed_hosts(request), {HOST, "www.edpb.europa.eu"})
        with self.assertRaises(s.RetrievalFailure) as caught:
            s.allowed_hosts(s.TargetRequest("t", URL, ("example.invalid",)))
        self.assertEqual(caught.exception.code, "redirect-host-not-official")

    def test_any_nonpublic_address_rejects_the_whole_answer_set(self):
        self.assertEqual(s.check_addresses([PUBLIC, PUBLIC, "2606:4700::1111"]), [PUBLIC, "2606:4700::1111"])
        for answers in (["10.0.0.1"], [PUBLIC, "127.0.0.1"], ["169.254.169.254"], ["192.168.1.1"], ["100.64.0.1"],
                        ["0.0.0.0"], ["224.0.0.1"], ["240.0.0.1"], ["::1"], ["fe80::1"], ["fc00::1"],
                        ["::ffff:93.184.216.34"], ["2002:5db8:d822::1"], ["2001::1"], ["not-an-address"],
                        [f"8.8.8.{index}" for index in range(17)]):
            with self.subTest(answers=answers[:2]), self.assertRaises(s.RetrievalFailure) as caught:
                s.check_addresses(answers)
            self.assertEqual(caught.exception.code, "unsafe-destination")
        with self.assertRaises(s.RetrievalFailure) as caught:
            s.check_addresses([])
        self.assertEqual(caught.exception.code, "dns-failed")
        self.assertEqual(len(s.check_addresses([f"8.8.8.{index}" for index in range(16)])), 16)


class FetchTests(unittest.TestCase):
    def test_success_retains_exact_bytes_and_pins_validated_address(self):
        transport = FakeTransport(responses={(HOST, target_of(URL)): FakeResponse(body=PAGE)})
        result = fetch(transport)
        self.assertIsNone(result.failure)
        self.assertEqual((result.content, result.final_url, result.status), (PAGE, URL, 200))
        self.assertEqual((result.media_type, result.charset, result.bytes_read), ("text/html", "utf-8", len(PAGE)))
        self.assertEqual(transport.calls[0], ("resolve", HOST))
        self.assertEqual(transport.calls[1][:4], ("get", HOST, PUBLIC, target_of(URL)))
        self.assertLessEqual(transport.calls[1][4], s.OPERATION_SECONDS)
        self.assertLessEqual(result.started_at, result.ended_at)

    def test_unsafe_targets_never_reach_dns_or_http(self):
        for url, code in ((f"http://{HOST}/", "unsafe-url"), ("https://example.invalid/", "host-not-official"),
                          (f"https://{HOST}:8080/", "unsafe-url")):
            transport = FakeTransport()
            with self.subTest(url=url):
                self.assertEqual(fetch(transport, url).failure, code)
                self.assertEqual(transport.calls, [])
        transport = FakeTransport()
        synthetic = s.fetch(s.TargetRequest("t", "https://example.invalid/x", synthetic=True), transport,
                            limit=1, deadline=time.monotonic() + 5)
        self.assertEqual((synthetic.failure, transport.calls), ("synthetic-target-not-fetched", []))
        self.assertEqual(fetch(transport, limit=0).failure, "download-budget-exhausted")
        self.assertEqual(transport.calls, [])

    def test_private_dns_answer_is_refused_before_connecting(self):
        transport = FakeTransport(dns={HOST: [PUBLIC, "10.1.2.3"]})
        self.assertEqual(fetch(transport).failure, "unsafe-destination")
        self.assertEqual([call[0] for call in transport.calls], ["resolve"])

    def test_redirects_are_revalidated_and_bounded(self):
        moved = f"https://{HOST}/moved"
        edpb = "https://www.edpb.europa.eu/doc"

        def redirect(location, status=302):
            return FakeResponse(status, [("Location", location)])
        transport = FakeTransport(responses={(HOST, target_of(URL)): redirect("/moved", 301),
                                             (HOST, "/moved"): redirect(edpb, 308),
                                             ("www.edpb.europa.eu", "/doc"): FakeResponse(body=PAGE)})
        result = fetch(transport, redirect_hosts=("www.edpb.europa.eu",))
        self.assertIsNone(result.failure)
        self.assertEqual((result.redirects, result.final_url), ((moved, edpb), edpb))
        self.assertEqual([call[1] for call in transport.calls if call[0] == "resolve"], [HOST, HOST, "www.edpb.europa.eu"])

        cases = {
            "unsafe-redirect": [edpb, "http://eur-lex.europa.eu/x", "https://127.0.0.1/", "https://evil.example/",
                                f"https://{HOST}:8443/", "//evil.example/x", f"https://u@{HOST}/", "/" + "a" * 4096],
            "redirect-loop": [URL],
            "invalid-response": [None],
        }
        for code, locations in cases.items():
            for location in locations:
                headers = [] if location is None else [("Location", location)]
                transport = FakeTransport(responses={(HOST, target_of(URL)): FakeResponse(302, headers)})
                with self.subTest(location=location):
                    result = fetch(transport)
                    self.assertEqual(result.failure, code)
                    self.assertEqual(result.redirects, ())
                    self.assertEqual(sum(call[0] == "get" for call in transport.calls), 1)
        twice = FakeTransport(responses={(HOST, target_of(URL)): FakeResponse(302, [("Location", "/a"), ("Location", "/b")])})
        self.assertEqual(fetch(twice).failure, "invalid-response")

    def test_public_to_private_redirect_is_refused_after_fresh_resolution(self):
        other = "https://curia.europa.eu/case"
        transport = FakeTransport(dns={"curia.europa.eu": ["192.168.0.10"]},
                                  responses={(HOST, target_of(URL)): FakeResponse(302, [("Location", other)])})
        result = fetch(transport, redirect_hosts=("curia.europa.eu",))
        self.assertEqual(result.failure, "unsafe-destination")
        self.assertEqual(result.redirects, (other,))
        self.assertEqual(transport.calls[-1], ("resolve", "curia.europa.eu"))

    def test_at_most_three_redirects_four_gets(self):
        responses = {(HOST, target_of(URL)): FakeResponse(302, [("Location", "/r1")])}
        for index in range(1, 5):
            responses[(HOST, f"/r{index}")] = FakeResponse(302, [("Location", f"/r{index + 1}")])
        transport = FakeTransport(responses=responses)
        result = fetch(transport)
        self.assertEqual(result.failure, "too-many-redirects")
        self.assertEqual(len(result.redirects), 3)
        self.assertEqual(sum(call[0] == "get" for call in transport.calls), 4)
        responses[(HOST, "/r3")] = FakeResponse(body=PAGE)
        self.assertIsNone(fetch(FakeTransport(responses=responses)).failure)

    def test_status_media_encoding_and_header_bounds(self):
        line = s.MAX_HEADER_LINE - 4 - len("X-Fill")
        cases = [
            (FakeResponse(404, body=b"missing"), "http-status"),
            (FakeResponse(304), "http-status"),
            (FakeResponse(headers=[("Content-Type", "image/png")]), "unsupported-media-type"),
            (FakeResponse(headers=[]), "unsupported-media-type"),
            (FakeResponse(headers=[*HTML, ("Content-Type", "text/plain")]), "invalid-response"),
            (FakeResponse(headers=[("Content-Type", "text/html; charset=\"" + "x" * 300 + "\"")]), "unsupported-media-type"),
            (FakeResponse(headers=[*HTML, ("Content-Encoding", "gzip")]), "compressed-response"),
            (FakeResponse(headers=[*HTML, ("Content-Length", "1"), ("Content-Length", "2")]), "invalid-response"),
            (FakeResponse(headers=[*HTML, ("Content-Length", "-1")]), "invalid-response"),
            (FakeResponse(headers=[*HTML, ("X-Fill", "a" * (line + 1))]), "header-limit"),
            (FakeResponse(headers=[*HTML, *[("X", "y")] * s.MAX_HEADERS]), "header-limit"),
            (FakeResponse(headers=[*HTML, *[("X-Fill", "a" * line)] * 8]), "header-limit"),
        ]
        for response, code in cases:
            with self.subTest(code=code, headers=[name for name, _ in response.headers][:3]):
                result = fetch(FakeTransport(responses={(HOST, target_of(URL)): response}))
                self.assertEqual(result.failure, code)
                self.assertIsNone(result.content)
                self.assertTrue(response.closed)
        accepted = [*HTML, *[("X-Fill", "a" * line)] * 7, ("Content-Encoding", "identity")]
        self.assertIsNone(fetch(FakeTransport(responses={(HOST, target_of(URL)): FakeResponse(headers=accepted, body=PAGE)})).failure)
        at_count = [*HTML, *[("X", "y")] * (s.MAX_HEADERS - 1)]
        self.assertIsNone(fetch(FakeTransport(responses={(HOST, target_of(URL)): FakeResponse(headers=at_count, body=PAGE)})).failure)

    def test_body_limit_boundary_and_early_content_length(self):
        limit = 3 * s.CHUNK_BYTES + 5
        exact = b"a" * limit
        ok = fetch(FakeTransport(responses={(HOST, target_of(URL)): FakeResponse(headers=[("Content-Type", "text/plain")], body=exact)}), limit=limit)
        self.assertEqual((ok.failure, ok.content), (None, exact))
        over = fetch(FakeTransport(responses={(HOST, target_of(URL)): FakeResponse(headers=[("Content-Type", "text/plain")], body=exact + b"a")}), limit=limit)
        self.assertEqual((over.failure, over.content, over.bytes_read), ("response-too-large", None, limit + 1))
        early = FakeResponse(headers=[*HTML, ("Content-Length", str(limit + 1))], body=exact)
        result = fetch(FakeTransport(responses={(HOST, target_of(URL)): early}), limit=limit)
        self.assertEqual((result.failure, result.bytes_read), ("response-too-large", 0))

    def test_slow_trickle_and_errors_become_safe_failures(self):
        clock = [0.0]

        def tick():
            clock[0] += 3
        trickle = FakeResponse(body=b"x" * (10 * s.CHUNK_BYTES), chunk_delay=tick)
        transport = FakeTransport(responses={(HOST, target_of(URL)): trickle})
        result = fetch(transport, deadline=10.0, clock=lambda: clock[0])
        self.assertEqual((result.failure, result.content), ("timeout", None))
        import ssl
        for error, code in ((TimeoutError(), "timeout"), (ssl.SSLCertVerificationError("PRIVATE"), "tls-failed"),
                            (s.RetrievalFailure("peer-mismatch"), "peer-mismatch")):
            with self.subTest(code=code):
                result = fetch(FakeTransport(errors={PUBLIC: error}))
                self.assertEqual((result.failure, result.content), (code, None))
        fallback = FakeTransport(dns={HOST: ["93.184.216.35", PUBLIC]}, errors={"93.184.216.35": ConnectionRefusedError()},
                                 responses={(HOST, target_of(URL)): FakeResponse(body=PAGE)})
        self.assertIsNone(fetch(fallback).failure)
        self.assertEqual([call[2] for call in fallback.calls if call[0] == "get"], ["93.184.216.35", PUBLIC])
        refused = FakeTransport(errors={PUBLIC: ConnectionRefusedError()})
        self.assertEqual(fetch(refused).failure, "connect-failed")

        class BrokenDns(FakeTransport):
            def resolve(self, host):
                raise socket.gaierror("PRIVATE")
        self.assertEqual(fetch(BrokenDns()).failure, "dns-failed")


class LocalListener:
    """Plain local TCP peer for wire checks; TLS is replaced by a recording fake context."""
    def __init__(self, reply: bytes):
        self.server = socket.create_server(("127.0.0.1", 0))
        self.port = self.server.getsockname()[1]
        self.reply, self.request = reply, b""
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        connection, _ = self.server.accept()
        with connection:
            while b"\r\n\r\n" not in self.request:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                self.request += chunk
            connection.sendall(self.reply)
        self.server.close()


class FakeContext:
    def __init__(self):
        self.server_hostnames = []

    def wrap_socket(self, sock, server_hostname):
        self.server_hostnames.append(server_hostname)
        return sock


class SystemTransportWireTests(unittest.TestCase):
    def test_pinned_connection_sends_only_fixed_headers_and_ignores_proxy_environment(self):
        listener = LocalListener(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 5\r\nSet-Cookie: a=b\r\n\r\nhello")
        context = FakeContext()
        transport = s.SystemTransport(context=context, port=listener.port)
        proxy = {"HTTPS_PROXY": "http://127.0.0.2:9", "https_proxy": "http://127.0.0.2:9", "ALL_PROXY": "http://127.0.0.2:9"}
        with patch.dict(os.environ, proxy):
            response = transport.get(HOST, "127.0.0.1", "/doc?x=1", 5)
        try:
            self.assertEqual((response.status, response.read(100)), (200, b"hello"))
        finally:
            response.close()
        listener.thread.join(5)
        self.assertEqual(context.server_hostnames, [HOST])
        lines = listener.request.decode().split("\r\n")
        self.assertEqual(lines[0], "GET /doc?x=1 HTTP/1.1")
        headers = {line.split(":", 1)[0].lower(): line.split(":", 1)[1].strip() for line in lines[1:] if line}
        self.assertEqual(set(headers), {"host", "accept-encoding", "user-agent", "accept", "connection"})
        self.assertEqual(headers["host"], f"{HOST}:{listener.port}")
        self.assertEqual((headers["accept-encoding"], headers["connection"]), ("identity", "close"))
        self.assertNotIn("cookie", headers)

    def test_peer_must_match_validated_address(self):
        connection = s._PinnedHTTPSConnection(HOST, "127.0.0.1", 443, 5, FakeContext())

        class Peer:
            closed = False

            def getpeername(self):
                return ("127.0.0.2", 443)

            def close(self):
                Peer.closed = True
        with patch("socket.create_connection", return_value=Peer()) as create, self.assertRaises(s.RetrievalFailure) as caught:
            connection.connect()
        create.assert_called_once_with(("127.0.0.1", 443), 5)
        self.assertEqual(caught.exception.code, "peer-mismatch")
        self.assertTrue(Peer.closed)

    def test_default_context_verifies_certificates_and_hostnames(self):
        import ssl
        context = s.SystemTransport().context
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)


class HangingTransport:
    """Picklable factory for the spawned helper; blocks like a stuck system resolver."""
    def resolve(self, host):
        time.sleep(60)

    def get(self, *args):
        raise AssertionError("unreachable")


class StaticTransport(FakeTransport):
    def __init__(self):
        super().__init__(responses={(HOST, target_of(URL)): lambda: FakeResponse(body=PAGE)})


class WorkerTests(unittest.TestCase):
    def test_helper_returns_staged_bytes_and_enforces_wall_deadline(self):
        requests = [s.TargetRequest("ok", URL), s.TargetRequest("fake", "https://example.invalid/x", synthetic=True),
                    s.TargetRequest("unsafe", "https://example.invalid/x")]
        results = s.retrieve(requests, transport_factory=StaticTransport)
        self.assertEqual([item.failure for item in results], [None, "synthetic-target-not-fetched", "host-not-official"])
        self.assertEqual(results[0].content, PAGE)
        started = time.monotonic()
        with patch.object(s, "STOP_SECONDS", 1.0):
            hung = s.retrieve([s.TargetRequest("hung", URL)], transport_factory=HangingTransport, target_seconds=0.5)
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual((hung[0].failure, hung[0].content), ("timeout", None))
        import multiprocessing
        self.assertEqual(multiprocessing.active_children(), [])

    def test_budgets_produce_explicit_attempts_without_workers(self):
        requests = [s.TargetRequest(f"t{index}", URL) for index in range(2)]
        with patch.object(s.multiprocessing.get_context("spawn"), "Process", side_effect=AssertionError("no helper")):
            results = s.retrieve(requests, transport_factory=StaticTransport, network_seconds=0)
        self.assertEqual([item.failure for item in results], ["network-budget-exhausted"] * 2)
        with self.assertRaises(ValueError):
            s.retrieve([s.TargetRequest("t", URL)] * 17)

    def test_unstoppable_helper_is_fatal(self):
        class Stuck:
            def join(self, timeout=None):
                pass

            def is_alive(self):
                return True

            def terminate(self):
                pass

            def kill(self):
                pass
        with patch.object(s, "STOP_SECONDS", 0), self.assertRaises(s.RetrievalHelperError):
            s._stop(Stuck())


if __name__ == "__main__":
    unittest.main()
