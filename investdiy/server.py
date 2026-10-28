"""Local server for the toolbox: home page, tool pages and data files, standard library only.

Usage:
  .venv/bin/python3 -m investdiy.server              # http://localhost:8765/
  .venv/bin/python3 -m investdiy.server --port 9000 --host 0.0.0.0

Routes:
  /                       home page (investdiy/web/index.html), lists every tool
  /api/tools.json         tool list as JSON (used by the home page; exported as a file of the same name, see export.py)
  /static/<path>          shared front-end assets (investdiy/web/static/: styles, kit.js, d3)
  /<slug>/                tool page (investdiy/<package>/web/index.html)
  /<slug>/<path>          the tool's own front-end files (investdiy/<package>/web/<path>)
  /<slug>/data/<file>     the tool's output data (investdiy/<package>/data/out/<file>)
"""

from __future__ import annotations

import argparse
import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .registry import TOOLS_DIR, discover

WEB = TOOLS_DIR / "web"
mimetypes.add_type("text/csv", ".csv")
mimetypes.add_type("text/javascript", ".js")


def _inside(base: Path, rel: str) -> Path | None:
    """Resolve base/rel and make sure it stays inside base (no ../ traversal)."""
    p = (base / rel).resolve()
    return p if p.is_relative_to(base.resolve()) and p.is_file() else None


def tools_payload(tools: dict) -> list[dict]:
    """Tool list for the home page (shared by the server and the static export)."""
    return [
        {"slug": t.slug, "url": f"/{t.slug}/", "asof": t.asof(meta), "update": t.update,
         "zh": {"title": t.title, "description": t.description, "kind": t.kind},
         "en": {"title": t.title_en, "description": t.description_en, "kind": t.kind_en}}
        for t, meta in tools.values()
    ]


class Handler(BaseHTTPRequestHandler):
    tools: dict = {}

    def log_message(self, fmt, *args):  # log only non-2xx/3xx responses
        if len(args) > 1 and str(args[1])[:1] not in "23":
            super().log_message(fmt, *args)

    def _send_file(self, path: Path | None) -> None:
        if path is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/json", "image/svg+xml"):
            ctype += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")  # data changes daily, always revalidate
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = unquote(urlsplit(self.path).path)
        if path in ("/", "/index.html"):
            return self._send_file(_inside(WEB, "index.html"))
        if path in ("/api/tools", "/api/tools.json"):
            return self._send_json(tools_payload(self.tools))
        if path.startswith("/static/"):
            return self._send_file(_inside(WEB / "static", path[len("/static/"):]))

        slug, _, rest = path.lstrip("/").partition("/")
        if slug not in self.tools:
            return self.send_error(HTTPStatus.NOT_FOUND)
        tool, _ = self.tools[slug]
        if path == f"/{slug}":
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", f"/{slug}/")
            self.end_headers()
            return
        if rest in ("", "index.html"):
            return self._send_file(_inside(tool.web, "index.html"))
        if rest.startswith("data/"):
            return self._send_file(_inside(tool.data, rest[len("data/"):]))
        return self._send_file(_inside(tool.web, rest))


def main() -> None:
    ap = argparse.ArgumentParser(description="Local toolbox server")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    Handler.tools = discover()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    host = "localhost" if a.host in ("127.0.0.1", "0.0.0.0") else a.host
    print(f"Home  http://{host}:{a.port}/", flush=True)
    for t, _ in Handler.tools.values():
        print(f"{t.kind_en}  http://{host}:{a.port}/{t.slug}/  {t.title_en}", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
