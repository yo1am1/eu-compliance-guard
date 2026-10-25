"""Bounded opt-in GETs of explicitly declared official sources; no crawl, credentials or evidence.

A retrieval records only which bytes an approved host served. It never establishes
binding status, completeness, applicability or currency for an assessment date.
The disposable worker exists to impose a wall deadline on blocking DNS/TLS/I/O; it
does not run target code and is not a security sandbox.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timezone
import http.client
import ipaddress
import multiprocessing
import os
import re
import socket
import ssl
import stat
import tempfile
import time
from urllib.parse import urljoin, urlsplit

from . import __version__

# Code-reviewed exact-host registry. It is a retrieval policy, not a list of all official law.
OFFICIAL_HOSTS = frozenset({
    "eur-lex.europa.eu", "curia.europa.eu", "commission.europa.eu",
    "digital-strategy.ec.europa.eu", "www.edpb.europa.eu",
})
MAX_URL_CHARS = 4096
MAX_ADDRESSES = 16
MAX_REDIRECTS = 3
MAX_TARGETS = 16
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 64 * 1024 * 1024
MAX_HEADERS = 100
MAX_HEADER_LINE = 8 * 1024
MAX_HEADER_BYTES = 64 * 1024
CHUNK_BYTES = 64 * 1024
OPERATION_SECONDS = 5.0
TARGET_SECONDS = 20.0
NETWORK_SECONDS = 300.0
STOP_SECONDS = 2.0
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
MEDIA_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain", "application/pdf"})
# http.client adds only Host and "Accept-Encoding: identity" to these fixed headers.
REQUEST_HEADERS = {
    "User-Agent": f"eu-compliance-guard/{__version__} (selected official-source retrieval)",
    "Accept": "text/html, application/xhtml+xml, text/plain, application/pdf",
    "Connection": "close",
}
_MEDIA = re.compile(r"^[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+$")
_CHARSET = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
FAILURES = {
    "synthetic-target-not-fetched": "Fictional fixture targets are never contacted.",
    "unsafe-url": "The URL is not a credential-free HTTPS URL on port 443.",
    "host-not-official": "The host is not in the reviewed official-source registry.",
    "redirect-host-not-official": "A selected redirect host is not in the reviewed official-source registry.",
    "unsafe-redirect": "A redirect destination failed URL or host validation.",
    "redirect-loop": "The redirect chain revisits a URL.",
    "too-many-redirects": "The redirect limit was exceeded.",
    "dns-failed": "The official host name could not be resolved.",
    "unsafe-destination": "The host resolved to a non-public or excessive address set.",
    "connect-failed": "No validated address accepted a connection.",
    "peer-mismatch": "The connected peer differs from the validated address.",
    "tls-failed": "TLS certificate or hostname verification failed.",
    "timeout": "The official source request exceeded its time limit.",
    "invalid-response": "The HTTP response was malformed.",
    "header-limit": "The response headers exceeded their limits.",
    "http-status": "The official source did not return HTTP 200.",
    "unsupported-media-type": "The response media type is not supported for review.",
    "compressed-response": "Compressed responses are refused rather than decompressed.",
    "response-too-large": "The response exceeded the download limit.",
    "download-budget-exhausted": "The run download budget was exhausted.",
    "network-budget-exhausted": "The run network time budget was exhausted.",
    "worker-failed": "The retrieval helper ended without a usable result.",
}


class RetrievalFailure(Exception):
    """A fixed, tool-owned failure code; never carries URLs, headers or bodies."""
    def __init__(self, code: str):
        self.code = code if code in FAILURES else "worker-failed"
        super().__init__(self.code)


class RetrievalHelperError(RuntimeError):
    """A worker that could not be stopped; the whole run must fail."""


@dataclass(frozen=True)
class TargetRequest:
    target_id: str
    url: str
    redirect_hosts: tuple[str, ...] = ()
    synthetic: bool = False


@dataclass(frozen=True)
class FetchResult:
    target_id: str
    requested_url: str
    started_at: str
    ended_at: str
    redirects: tuple[str, ...] = ()
    final_url: str | None = None
    status: int | None = None
    media_type: str | None = None
    charset: str | None = None
    bytes_read: int = 0
    content: bytes | None = None
    failure: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def allowed_hosts(request: TargetRequest) -> frozenset[str]:
    """The target host plus selected redirect hosts, each required to be in the registry."""
    if any(host not in OFFICIAL_HOSTS for host in request.redirect_hosts):
        raise RetrievalFailure("redirect-host-not-official")
    host, _ = check_url(request.url, OFFICIAL_HOSTS)
    return frozenset({host, *request.redirect_hosts})


def check_url(url: str, hosts: frozenset[str]) -> tuple[str, str]:
    """Return (host, request target) for an exact registered HTTPS URL, or refuse it."""
    if (not isinstance(url, str) or len(url) > MAX_URL_CHARS or not url.isascii()
            or any(char.isspace() or ord(char) < 32 or ord(char) == 127 or char == "\\" for char in url)):
        raise RetrievalFailure("unsafe-url")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise RetrievalFailure("unsafe-url") from None
    host = parts.hostname
    if (parts.scheme != "https" or "#" in url or port not in (None, 443) or not host
            or parts.netloc not in (host, host + ":443") or "%" in parts.netloc):
        raise RetrievalFailure("unsafe-url")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise RetrievalFailure("unsafe-url")
    if host not in hosts:
        raise RetrievalFailure("host-not-official")
    target = url[len(parts.scheme) + 3 + len(parts.netloc):]
    if target and not target.startswith(("/", "?")):
        raise RetrievalFailure("unsafe-url")
    return host, "/" + target.removeprefix("/") if target else "/"


def check_addresses(addresses: list[str]) -> list[str]:
    """Reject the whole answer set if any address is not a plain global unicast address."""
    unique = list(dict.fromkeys(addresses))
    if not unique:
        raise RetrievalFailure("dns-failed")
    if len(unique) > MAX_ADDRESSES:
        raise RetrievalFailure("unsafe-destination")
    for value in unique:
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            raise RetrievalFailure("unsafe-destination") from None
        mapped = address.version == 6 and (address.ipv4_mapped or address.sixtofour or address.teredo)
        if (mapped or not address.is_global or address.is_multicast or address.is_private or address.is_reserved
                or address.is_loopback or address.is_link_local or address.is_unspecified):
            raise RetrievalFailure("unsafe-destination")
    return unique


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to one validated numeric address; TLS and Host still use the original name."""
    def __init__(self, host: str, address: str, port: int, timeout: float, context: ssl.SSLContext):
        super().__init__(host, port, timeout=timeout, context=context)
        self._address = address

    def connect(self) -> None:
        sock = socket.create_connection((self._address, self.port), self.timeout)
        try:
            if ipaddress.ip_address(sock.getpeername()[0]) != ipaddress.ip_address(self._address):
                raise RetrievalFailure("peer-mismatch")
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


class _Response:
    def __init__(self, connection: http.client.HTTPConnection, response: http.client.HTTPResponse):
        self._connection, self._response = connection, response
        self.status = response.status
        self.headers = response.getheaders()

    def read(self, size: int) -> bytes:
        return self._response.read(size)

    def close(self) -> None:
        try:
            self._response.close()
        finally:
            self._connection.close()


class SystemTransport:
    """System DNS and verified TLS; http.client reads no proxy, cookie or .netrc settings."""
    def __init__(self, context: ssl.SSLContext | None = None, port: int = 443):
        self.context = context or ssl.create_default_context()
        self.port = port

    def resolve(self, host: str) -> list[str]:
        infos = socket.getaddrinfo(host, self.port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        return [info[4][0] for info in infos if info[0] in (socket.AF_INET, socket.AF_INET6)]

    def get(self, host: str, address: str, target: str, timeout: float) -> _Response:
        connection = _PinnedHTTPSConnection(host, address, self.port, timeout, self.context)
        try:
            connection.request("GET", target, headers=REQUEST_HEADERS)
            return _Response(connection, connection.getresponse())
        except BaseException:
            connection.close()
            raise


def _media_type(headers: list[tuple[str, str]]) -> tuple[str, str | None]:
    values = [value for name, value in headers if name.lower() == "content-type"]
    if len(values) != 1:
        raise RetrievalFailure("unsupported-media-type" if not values else "invalid-response")
    essence, *parameters = values[0].split(";")
    essence = essence.strip().lower()
    charset = None
    for parameter in parameters:
        name, _, value = parameter.partition("=")
        if name.strip().lower() == "charset":
            charset = value.strip().strip('"').lower()
    if not _MEDIA.match(essence) or essence not in MEDIA_TYPES or (charset is not None and not _CHARSET.match(charset)):
        raise RetrievalFailure("unsupported-media-type")
    return essence, charset


def fetch(request: TargetRequest, transport, *, limit: int, deadline: float,
          clock=time.monotonic, now=utc_now) -> FetchResult:
    """One target's bounded GETs and redirects; every failure becomes a safe result."""
    started = now()
    state = {"redirects": [], "status": None, "media_type": None, "charset": None, "bytes_read": 0}

    def remaining() -> float:
        left = deadline - clock()
        if left <= 0:
            raise RetrievalFailure("timeout")
        return min(OPERATION_SECONDS, left)

    def result(failure=None, **values) -> FetchResult:
        return FetchResult(target_id=request.target_id, requested_url=request.url, started_at=started, ended_at=now(),
                           redirects=tuple(state["redirects"]), status=state["status"], media_type=state["media_type"],
                           charset=state["charset"], bytes_read=state["bytes_read"], failure=failure, **values)

    try:
        if request.synthetic:
            raise RetrievalFailure("synthetic-target-not-fetched")
        if limit <= 0:
            raise RetrievalFailure("download-budget-exhausted")
        hosts = allowed_hosts(request)
        url = request.url
        seen = {url}
        for hop in range(MAX_REDIRECTS + 1):
            host, target = check_url(url, hosts)
            addresses = check_addresses(transport.resolve(host))
            response = None
            for address in addresses:
                try:
                    response = transport.get(host, address, target, remaining())
                    break
                except (ssl.SSLError, TimeoutError):
                    raise
                except OSError:
                    continue  # Only another address from the same validated answer set, within the deadline.
            if response is None:
                raise RetrievalFailure("connect-failed")
            try:
                state["status"] = response.status
                headers = list(response.headers)
                lines = [len(name) + len(value) + 4 for name, value in headers]
                if len(headers) > MAX_HEADERS or any(line > MAX_HEADER_LINE for line in lines) or sum(lines) > MAX_HEADER_BYTES:
                    raise RetrievalFailure("header-limit")
                if response.status in REDIRECT_STATUSES:
                    locations = [value for name, value in headers if name.lower() == "location"]
                    if len(locations) != 1:
                        raise RetrievalFailure("invalid-response")
                    if hop == MAX_REDIRECTS:
                        raise RetrievalFailure("too-many-redirects")
                    if len(locations[0]) > MAX_URL_CHARS:
                        raise RetrievalFailure("unsafe-redirect")
                    location = urljoin(url, locations[0])
                    try:
                        check_url(location, hosts)
                    except RetrievalFailure:
                        raise RetrievalFailure("unsafe-redirect") from None
                    if location in seen:
                        raise RetrievalFailure("redirect-loop")
                    seen.add(location)
                    state["redirects"].append(location)
                    url = location
                    continue
                if response.status != 200:
                    raise RetrievalFailure("http-status")
                if any(name.lower() == "content-encoding" and value.strip().lower() != "identity" for name, value in headers):
                    raise RetrievalFailure("compressed-response")
                state["media_type"], state["charset"] = _media_type(headers)
                lengths = [value.strip() for name, value in headers if name.lower() == "content-length"]
                if len(set(lengths)) > 1 or (lengths and not lengths[0].isdigit()):
                    raise RetrievalFailure("invalid-response")
                if lengths and int(lengths[0]) > limit:
                    raise RetrievalFailure("response-too-large")
                chunks = []
                while True:
                    remaining()
                    chunk = response.read(min(CHUNK_BYTES, limit - state["bytes_read"] + 1))
                    if not chunk:
                        break
                    state["bytes_read"] += len(chunk)
                    if state["bytes_read"] > limit:
                        raise RetrievalFailure("response-too-large")
                    chunks.append(chunk)
                return result(final_url=url, content=b"".join(chunks))
            finally:
                response.close()
        raise RetrievalFailure("too-many-redirects")
    except RetrievalFailure as failure:
        return result(failure.code)
    except TimeoutError:
        return result("timeout")
    except (ssl.SSLError, ssl.CertificateError):
        return result("tls-failed")
    except socket.gaierror:
        return result("dns-failed")
    except http.client.HTTPException:
        return result("invalid-response")
    except (OSError, ValueError):
        return result("connect-failed")


def _worker(request: TargetRequest, transport_factory, limit: int, seconds: float, staged: str, connection) -> None:
    try:
        outcome = fetch(request, transport_factory(), limit=limit, deadline=time.monotonic() + seconds)
        if outcome.content is not None:
            fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(outcome.content)
        connection.send({item.name: getattr(outcome, item.name) for item in fields(outcome) if item.name != "content"}
                        | {"staged": outcome.content is not None})
    except BaseException:
        try:
            connection.send({"failure": "worker-failed"})
        except BaseException:
            pass
    finally:
        connection.close()


def _stop(process) -> None:
    process.join(0.05)
    if process.is_alive():
        process.terminate()
        process.join(STOP_SECONDS)
    if process.is_alive():
        process.kill()
        process.join(STOP_SECONDS)
    if process.is_alive():
        raise RetrievalHelperError("retrieval helper could not be stopped")


def _read_staged(path: str, expected: int, limit: int) -> bytes | None:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return None
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size != expected or expected > limit:
            return None
        content = os.read(fd, expected + 1) if expected else b""
        while len(content) < expected + 1:
            chunk = os.read(fd, expected + 1 - len(content))
            if not chunk:
                break
            content += chunk
        return content if len(content) == expected else None
    finally:
        os.close(fd)
        os.unlink(path)


def _from_message(request: TargetRequest, message, started: str, content: bytes | None) -> FetchResult:
    try:
        values = {key: message[key] for key in ("started_at", "ended_at", "final_url", "status", "media_type",
                                                "charset", "bytes_read", "failure")}
        redirects = tuple(message["redirects"])
        if (message["target_id"] != request.target_id or message["requested_url"] != request.url
                or not all(isinstance(item, str) for item in redirects) or type(values["bytes_read"]) is not int
                or (values["failure"] is not None and values["failure"] not in FAILURES)
                or (values["failure"] is None) != (content is not None)):
            raise ValueError
        return FetchResult(target_id=request.target_id, requested_url=request.url, redirects=redirects, content=content, **values)
    except (KeyError, TypeError, ValueError):
        return FetchResult(target_id=request.target_id, requested_url=request.url, started_at=started,
                           ended_at=utc_now(), failure="worker-failed")


def retrieve(requests: list[TargetRequest], *, transport_factory=SystemTransport,
             target_seconds: float = TARGET_SECONDS, network_seconds: float = NETWORK_SECONDS) -> list[FetchResult]:
    """Fetch targets sequentially, one disposable helper at a time, within fixed bounds."""
    if len(requests) > MAX_TARGETS:
        raise ValueError("too many retrieval targets")
    context = multiprocessing.get_context("spawn")
    network_deadline = time.monotonic() + network_seconds
    used = 0
    results = []
    with tempfile.TemporaryDirectory(prefix="eucg-fetch-") as staging:
        os.chmod(staging, 0o700)
        for index, request in enumerate(requests):
            started = utc_now()
            left = network_deadline - time.monotonic()
            limit = min(MAX_RESPONSE_BYTES, MAX_DOWNLOAD_BYTES - used)
            refusal = ("synthetic-target-not-fetched" if request.synthetic else "network-budget-exhausted" if left <= 0
                       else "download-budget-exhausted" if limit <= 0 else None)
            if refusal is None:
                try:
                    allowed_hosts(request)
                except RetrievalFailure as failure:
                    refusal = failure.code
            if refusal is not None:
                results.append(FetchResult(target_id=request.target_id, requested_url=request.url,
                                           started_at=started, ended_at=utc_now(), failure=refusal))
                continue
            seconds = min(target_seconds, left)
            staged = os.path.join(staging, f"{index}.body")
            receiver, sender = context.Pipe(duplex=False)
            process = context.Process(target=_worker, args=(request, transport_factory, limit, seconds, staged, sender),
                                      daemon=True)
            message = None
            try:
                process.start()
                sender.close()
                if receiver.poll(seconds):
                    message = receiver.recv()
            except (EOFError, OSError):
                message = None
            finally:
                receiver.close()
                _stop(process)
            if message is None:
                outcome = FetchResult(target_id=request.target_id, requested_url=request.url, started_at=started,
                                      ended_at=utc_now(), failure="timeout")
            else:
                content = None
                if isinstance(message, dict) and message.get("staged") is True and type(message.get("bytes_read")) is int:
                    content = _read_staged(staged, message["bytes_read"], limit)
                outcome = _from_message(request, message if isinstance(message, dict) else {}, started, content)
            used += min(outcome.bytes_read, limit + 1)
            results.append(outcome)
    return results
