"""Discover tools under investdiy/: any sub-package whose __init__.py defines a TOOL dict and that has web/index.html."""

from __future__ import annotations

import csv
import importlib
from dataclasses import dataclass
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
RESERVED = {"api", "static", "common", "web"}  # path segments that cannot be used as a slug


@dataclass
class Tool:
    slug: str
    title: str
    description: str
    kind: str
    package: str
    root: Path            # package directory
    update: str = ""
    title_en: str = ""
    description_en: str = ""
    kind_en: str = ""
    visibility: str = "local"  # public export requires an explicit opt-in

    @property
    def web(self) -> Path:
        return self.root / "web"

    @property
    def data(self) -> Path:
        return self.root / "data" / "out"

    def asof(self, meta: dict) -> str:
        f = meta.get("asof_file")
        if not f or not (self.root / f).exists():
            return ""
        with (self.root / f).open(encoding="utf-8") as fh:
            row = next(csv.DictReader(fh), None)
        return (row or {}).get("as_of", "")


def discover(*, public_only: bool = False) -> dict[str, tuple[Tool, dict]]:
    """Discover all local tools, optionally selecting only explicitly public ones."""
    found: dict[str, tuple[Tool, dict]] = {}
    for d in sorted(TOOLS_DIR.iterdir()):
        if not (d / "__init__.py").exists() or not (d / "web" / "index.html").exists():
            continue
        mod = importlib.import_module(f"investdiy.{d.name}")
        meta = getattr(mod, "TOOL", None)
        if not meta:
            continue
        slug = meta["slug"]
        if slug in RESERVED or slug in found:
            raise ValueError(f"Duplicate or reserved tool slug: {slug} ({d.name})")
        visibility = meta.get("visibility", "local")
        if visibility not in ("local", "public"):
            raise ValueError(f"Invalid tool visibility: {visibility!r} ({d.name}); use 'local' or 'public'")
        tool = Tool(slug=slug, title=meta["title"], description=meta.get("description", ""),
                    kind=meta.get("kind", "工具"), package=d.name, root=d, update=meta.get("update", ""),
                    title_en=meta.get("title_en", meta["title"]), description_en=meta.get("description_en", ""),
                    kind_en=meta.get("kind_en", "Tool"), visibility=visibility)
        found[slug] = (tool, meta)
    return {slug: entry for slug, entry in found.items() if not public_only or entry[0].visibility == "public"}
