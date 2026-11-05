"""Check that every host in the official retrieval registry still answers over HTTPS.

Network use needs consent: run it only with --consent (or `make verify-hosts`). It sends one
GET to each host's root and prints the status; it never runs in the unit tests. A host that
fails is a review gap to record in docs/official-hosts.md, never a reason to fall back to
another site.
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request

from eu_compliance_guard import __version__
from eu_compliance_guard.sources import OFFICIAL_HOSTS


def check(host: str, timeout: float = 15.0) -> str:
    request = urllib.request.Request(f"https://{host}/", headers={"User-Agent": f"eu-compliance-guard/{__version__}"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return f"reachable (HTTP {response.status})"
    except urllib.error.HTTPError as error:
        # An answer over verified TLS still shows the host is live; the status is recorded as seen.
        return f"reachable (HTTP {error.code})"
    except (urllib.error.URLError, OSError) as error:
        return f"unreachable ({type(getattr(error, 'reason', error)).__name__})"


def main(argv: list[str]) -> int:
    if argv != ["--consent"]:
        print("verify-hosts sends one HTTPS request to each official host; rerun with --consent", file=sys.stderr)
        return 2
    failed = 0
    for host in sorted(OFFICIAL_HOSTS):
        result = check(host)
        failed += result.startswith("unreachable")
        print(f"{host}\t{result}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
