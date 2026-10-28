"""Export the toolbox as a static site.

The only dynamic part of the local server (server.py) is /api/tools.json, which is written out as a
static file of the same name; everything else is copied as is, so the exported site behaves like localhost
and can be served by any static file host.

Usage:
  .venv/bin/python3 -m investdiy.export                    # export to investdiy/dist/
  .venv/bin/python3 -m investdiy.export --out /tmp/site    # export elsewhere
  cd investdiy/dist && python3 -m http.server              # preview the export

Note: the export includes each tool's data/out/ CSV files; check the data providers' terms before
hosting it publicly.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from .registry import TOOLS_DIR, discover
from .server import tools_payload

DIST = TOOLS_DIR / "dist"
WEB = TOOLS_DIR / "web"


def build(dist: Path = DIST) -> list[str]:
    if dist.exists():
        # only replace an empty folder or a previous export, never an arbitrary directory
        if any(dist.iterdir()) and not (dist / "api" / "tools.json").exists():
            raise SystemExit(f"{dist} is not empty and is not a previous export; choose another --out")
        shutil.rmtree(dist)
    shutil.copytree(WEB, dist)  # home page + /static
    # the home page top bar says "static snapshot" instead of "local server"
    home = dist / "index.html"
    home.write_text(home.read_text(encoding="utf-8").replace('data-i18n="home.server"', 'data-i18n="home.snapshot"'),
                    encoding="utf-8")

    tools = discover()
    (dist / "api").mkdir()
    (dist / "api" / "tools.json").write_text(json.dumps(tools_payload(tools), ensure_ascii=False), encoding="utf-8")

    built = []
    for tool, _ in tools.values():
        out = dist / tool.slug
        shutil.copytree(tool.web, out)
        if tool.data.exists():
            shutil.copytree(tool.data, out / "data", ignore=shutil.ignore_patterns("*.tmp"))
        else:
            print(f"  ! {tool.slug} has no data/out/; its page will fail to load (run its update command first)")
        built.append(tool.slug)

    (dist / "404.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>404</title>'
        '<p style="font-family:sans-serif;padding:2rem">页面不存在 · Page not found. <a href="/">投研工具箱 · Research Toolkit</a></p>',
        encoding="utf-8")
    size = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
    print(f"[export] {dist}  {len(built)} tool(s): {', '.join(built)}  {size / 1e6:.1f} MB in total")
    return built


def main() -> None:
    ap = argparse.ArgumentParser(description="Export the static site")
    ap.add_argument("--out", type=Path, default=DIST, help=f"output folder (default: {DIST})")
    a = ap.parse_args()
    build(a.out.resolve())


if __name__ == "__main__":
    main()
