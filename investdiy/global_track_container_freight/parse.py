"""Read SSE's dated tables without collapsing empty cells or executing page scripts.

The expanded table grid handles row/column spans. GCSP and BRCVI additionally
embed literal data in scripts; only those literals are decoded, never evaluated.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import date
from html.parser import HTMLParser

from .indices import SERIES, match_series

PERIOD = re.compile(r"(?<!\d)\d{4}-\d{2}(?:-\d{2})?(?![\d-])")
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)")
CURRENT_FIELDS = ["index", "series", "name", "name_en", "unit", "weight", "date", "value",
                  "prev_date", "prev", "change", "change_unit", "period"]


def number(text: str) -> str:
    text = text.strip().replace(",", "").replace("−", "-").removesuffix("%")
    return text if NUMBER.fullmatch(text) and math.isfinite(float(text)) else ""


def period(text: str) -> tuple[str, str]:
    found = PERIOD.search(text)
    if not found:
        return "", ""
    raw = found.group()
    try:
        d = date.fromisoformat(raw + "-01" if len(raw) == 7 else raw)
    except ValueError:
        return "", ""
    return d.isoformat(), raw


class Tables(HTMLParser):
    """Expand spans to a rectangular grid; collect only table text and nearby titles."""
    def __init__(self):
        super().__init__()
        self.tables = []
        self.titles = []
        self._title = None
        self._last_title = ""
        self._rows = None
        self._spans = {}
        self._cell = None
        self._row = None
        self._col = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div" and "title2" in attrs.get("class", "").split():
            self._title = []
        if tag == "table":
            self._rows, self._spans = [], {}
        elif tag == "tr" and self._rows is not None:
            self._row = {}
            for col, (left, value) in list(self._spans.items()):
                self._row[col] = value
                if left == 1:
                    del self._spans[col]
                else:
                    self._spans[col] = (left - 1, value)
            self._col = 0
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
            self._width = max(1, int(attrs.get("colspan", 1)))
            self._height = max(1, int(attrs.get("rowspan", 1)))
        elif tag in ("br", "p"):
            if self._cell is not None:
                self._cell.append(" ")

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)
        if self._title is not None:
            self._title.append(data)

    def handle_endtag(self, tag):
        if tag == "div" and self._title is not None:
            self._last_title = " ".join("".join(self._title).split())
            self._title = None
        if tag in ("td", "th") and self._cell is not None:
            text = " ".join("".join(self._cell).split())
            while self._col in self._row:
                self._col += 1
            for offset in range(self._width):
                col = self._col + offset
                # Colspan continuation cells are empty, not repeated labels.
                value = text if offset == 0 else ""
                self._row[col] = value
                if self._height > 1:
                    self._spans[col] = (self._height - 1, value)
            self._col += self._width
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self._rows.append([self._row.get(c, "") for c in range(max(self._row, default=-1) + 1)])
            self._row = None
        elif tag == "table" and self._rows is not None:
            self.tables.append(self._rows)
            self.titles.append(self._last_title)
            self._rows = None


def identity(index: str, label: str, unit: str, context: str = "") -> tuple[str, str]:
    key = match_series(index, label) if not context else None
    if key:
        name_en = next(r[3] for r in SERIES[index] if r[0] == key)
        return key, name_en
    # Labels, vessel sizes, parent groups and units distinguish similarly named routes.
    normalized = re.sub(r"\s+", "", f"{context}|{label}|{unit}")
    key = "s_" + hashlib.sha256(normalized.encode()).hexdigest()[:16]
    # Preserve official bilingual labels; unprovided translations stay as source labels.
    return key, f"{context} / {label}" if context else label


def item(index, label, unit, d, value, *, context="", weight="", prev_date="", prev="", change="", change_unit="", raw_period=""):
    key, name_en = identity(index, label, unit, context)
    return dict(zip(CURRENT_FIELDS, [index, key, f"{context} / {label}" if context else label,
                name_en, unit, weight, d, number(value), prev_date, number(prev), number(change), change_unit, raw_period or d]))


def script_rows(html: str) -> list[list[str]]:
    rows = []
    for block in re.findall(r"row\s*=\s*\[\]\s*;(.*?)arr\[\d+\]\s*=\s*row", html, re.S):
        cells = {int(i): v for i, v in re.findall(r"row\[(\d+)\]\s*=\s*'([^']*)'", block)}
        if cells:
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
    return rows


def parse_page(index: str, html: str) -> list[dict]:
    p = Tables()
    p.feed(html)
    if index == "brcvi" and p.tables:
        # The first branch is the current (post-2021) methodology.
        block = re.search(r'\$\("#table_row"\)\.after\(\$\((.*?)\)\)', html, re.S)
        if block:
            literals = re.findall(r'"(?:\\.|[^"\\])*"', block.group(1))
            extra = Tables()
            extra.feed("<table>" + "".join(json.loads(s) for s in literals) + "</table>")
            if extra.tables:
                p.tables[0].extend(extra.tables[0])
    if index.startswith("gcspi"):
        return parse_reliability(index, p, html)
    out = []
    for table, title in zip(p.tables, p.titles):
        if not table:
            continue
        title_date, title_period = period(title)
        if index == "ccri" and table[0][0] == "职务":
            for row in table[1:]:
                for col, ship in enumerate(table[0][1:], 1):
                    if col < len(row) and title_date:
                        out.append(item(index, row[0], "USD/month", title_date, row[col], context=ship))
            continue
        header = table[0]
        dates = [(c, *period(h)) for c, h in enumerate(header) if period(h)[0]]
        if not dates and title_date:
            cols = [c for c, h in enumerate(header) if "本期" in h or "指数/日租金" in h]
            dates = [(c, title_date, title_period) for c in cols]
        if not dates:
            continue
        # CSI puts two independent index/value/change groups on each row.
        groups = [(0, dates)] if index != "csi" else [(0, dates[:1]), (3, dates[1:])]
        context = ""
        for row in table[1:]:
            row = row + [""] * max(0, len(header) - len(row))
            for label_col, dated_cols in groups:
                if not dated_cols or not row[label_col] or row[label_col].startswith("分航线"):
                    continue
                col, d, raw = dated_cols[-1]
                label = row[label_col]
                unit_col = next((c for c, h in enumerate(header) if h == "单位"), None)
                unit = row[unit_col] if unit_col is not None else ""
                if not unit:
                    unit = "CNY/tonne" if index in {"cbofi", "cbgfi", "cctfi_coastal"} and "指数" not in label else "points"
                unit = {"点": "points", "美元/TEU": "USD/TEU", "美元/FEU": "USD/FEU", "元/吨": "CNY/tonne", "美元/吨": "USD/tonne", "美元/天": "USD/day", "元/天": "CNY/day", "万美元": "USD 10,000", "美元/天(标准航速)": "USD/day (standard speed)", "美元/天(经济航速)": "USD/day (eco speed)"}.get(unit, unit)
                details = [row[c] for c, h in enumerate(header[:col]) if c != label_col and row[c] and any(w in h for w in ("船型", "载重吨", "载货量", "货量", "货种", "合约类型"))]
                if details:
                    label += " · " + " · ".join(details)
                weight = next((row[c] for c, h in enumerate(header) if h == "权重"), "")
                if index in {"srfi", "brcvi"} and ("“海上丝绸之路”" in label or "中国（上海）" in label):
                    context = label
                    row_context = ""
                else:
                    row_context = context
                prev_col, prev_date, _ = dated_cols[0] if len(dated_cols) > 1 else (0, "", "")
                change_header = header[col + 1] if col + 1 < len(header) else ""
                change_unit = "%" if "%" in change_header else unit
                out.append(item(index, label, unit, d, row[col], context=row_context,
                                weight=weight, prev_date=prev_date, prev=row[prev_col] if prev_date else "",
                                change=row[col + 1] if col + 1 < len(row) else "", change_unit=change_unit, raw_period=raw))
    return out


def parse_reliability(index: str, p: Tables, html: str) -> list[dict]:
    if not p.titles:
        return []
    d, raw = period(p.titles[0])
    if not d:
        return []
    out = []
    if index == "gcspi":
        for row in p.tables[0][1:]:
            out.append(item(index, row[0], "%", d, row[1], change=row[2], change_unit="pp", raw_period=raw))
        rows = p.tables[1][2:] if len(p.tables) > 1 else []
    else:
        rows = script_rows(html)
    if index == "gcspi_port":
        metrics = [(1, "准班率 / Reliability", "%", 2), (3, "挂靠数 / Calls", "calls", 4),
                   (5, "班期综合服务水平 / Service level", "points", None),
                   (8, "在港时间 / Port time", "days", None), (7, "在泊时间 / Berth time", "days", None)]
    else:
        metrics = [(1, "到离港 / Arrival-departure", "%", 2), (3, "收发货 / Receipt-delivery", "%", 4)]
    for row in rows:
        for col, label, unit, chg in metrics:
            if col < len(row):
                out.append(item(index, row[0], unit, d, row[col], context=label,
                                change=row[chg] if chg is not None else "", change_unit="pp" if unit == "%" else unit, raw_period=raw))
    return out
