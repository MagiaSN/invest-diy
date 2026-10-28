"""HTTP requests: GET with retries, plus a DNS-over-HTTPS fallback.

Some networks (including some sandboxed environments) fail to resolve hosts such as szse.cn or
cninfo.com.cn even though TCP 443 is reachable. ensure_resolvable() looks the IP up through
Cloudflare DoH and patches socket.getaddrinfo, which is transparent to requests.
"""

from __future__ import annotations

import socket
import time

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/132.0 Safari/537.36"

_DNS_OVERRIDE: dict[str, str] = {}
_orig_getaddrinfo = socket.getaddrinfo


def _patched_getaddrinfo(host, *args, **kwargs):
    return _orig_getaddrinfo(_DNS_OVERRIDE.get(host, host), *args, **kwargs)


def ensure_resolvable(host: str) -> None:
    """Fall back to DoH when local DNS resolution fails; do nothing if it resolves."""
    try:
        _orig_getaddrinfo(host, 443)
        return
    except socket.gaierror:
        pass
    r = requests.get(
        "https://cloudflare-dns.com/dns-query",
        params={"name": host, "type": "A"},
        headers={"accept": "application/dns-json"},
        timeout=10,
    )
    ips = [a["data"] for a in r.json().get("Answer", []) if a.get("type") == 1]
    if not ips:
        raise RuntimeError(f"DoH lookup failed: {host}")
    _DNS_OVERRIDE[host] = ips[0]
    socket.getaddrinfo = _patched_getaddrinfo


def get(url: str, *, params=None, headers=None, retries: int = 3, timeout: int = 30) -> requests.Response:
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA, **(headers or {})}, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == retries - 1:
                raise
            time.sleep(1.5 * (i + 1))
    raise AssertionError
