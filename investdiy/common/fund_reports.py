"""Fund periodic reports: listing, download and parsing of the holder tables.

Sources:
  - announcement list: api.fund.eastmoney.com/f10/JJGG?fundcode=<code>&type=3 (type=3 = periodic reports), needs a Referer
  - PDF: pdf.dfcfw.com/pdf/H2_<announcement id>_1.pdf

Three tables are parsed (pdfplumber table extraction; pypdfium2 first locates the pages so that text is
not extracted page by page):
  - top-ten holders of the listed fund at period end: annual reports only (and some interim reports),
    with holder names
  - single investors holding 20% or more of the fund during the period: in quarterly, interim and annual
    reports; only "institution / individual" is given, no name, but with opening, created, redeemed and
    closing units
  - number of holders and holder structure at period end: interim and annual reports; total units held by
    institutions (feeder funds listed separately and excluded), an upper bound on national-team holdings
"""

from __future__ import annotations

import io
import re
import threading
from dataclasses import dataclass, field, asdict

import pdfplumber
import pypdfium2

from . import net

PARSER_VERSION = 2  # bump when parsing changes so callers invalidate old caches

LIST_URL = "https://api.fund.eastmoney.com/f10/JJGG"
PDF_URL = "https://pdf.dfcfw.com/pdf/H2_{id}_1.pdf"
REFERER = {"Referer": "https://fundf10.eastmoney.com/"}

_PERIOD_END = {"年度报告": "12-31", "中期报告": "06-30", "半年度报告": "06-30",
               "第1季度报告": "03-31", "第2季度报告": "06-30", "第3季度报告": "09-30", "第4季度报告": "12-31",
               "第一季度报告": "03-31", "第二季度报告": "06-30", "第三季度报告": "09-30", "第四季度报告": "12-31"}


@dataclass
class Report:
    id: str
    title: str
    published: str
    period_end: str      # YYYY-MM-DD
    kind: str            # annual / interim / quarterly


def list_reports(code: str, since_year: int = 2023) -> list[Report]:
    """Periodic reports (excluding summaries and English versions), in report-period order."""
    out: dict[tuple[str, str], Report] = {}
    page = 1
    while True:
        r = net.get(LIST_URL, params={"fundcode": code, "pageIndex": page, "pageSize": 50, "type": 3}, headers=REFERER)
        d = r.json()
        rows = d.get("Data") or []
        for x in rows:
            title = x.get("TITLE", "")
            if "摘要" in title or "英文" in title:
                continue
            m = re.search(r"(\d{4})年(年度报告|中期报告|半年度报告|第[1-4一二三四]季度报告)", title)
            if not m or int(m.group(1)) < since_year:
                continue
            kind = "annual" if m.group(2) == "年度报告" else "interim" if "中期" in m.group(2) or "半年" in m.group(2) else "quarterly"
            rep = Report(id=x["ID"], title=title, published=(x.get("PUBLISHDATEDesc") or x.get("PUBLISHDATE", ""))[:10],
                         period_end=f"{m.group(1)}-{_PERIOD_END[m.group(2)]}", kind=kind)
            key = (rep.period_end, kind)
            if key not in out or rep.published > out[key].published:  # a corrected version replaces the original
                out[key] = rep
        if page * 50 >= (d.get("TotalCount") or 0) or not rows:
            break
        if min((x.get("PUBLISHDATEDesc") or "9999")[:4] for x in rows) < str(since_year):
            break
        page += 1
    return sorted(out.values(), key=lambda r: (r.period_end, r.kind))


def download_pdf(report_id: str) -> bytes:
    return net.get(PDF_URL.format(id=report_id), timeout=90).content


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

@dataclass
class HolderTables:
    top10: list[dict] = field(default_factory=list)      # {rank, name, shares, pct}
    big: list[dict] = field(default_factory=list)        # {seq, investor_type, interval, begin, buy, sell, end, pct}
    total_shares: float | None = None                    # total fund units at period end, if found
    inst_shares: float | None = None                     # units held by institutions at period end (interim / annual only)
    pending_inst: bool = False                           # holder-structure header seen, data row on the next page

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("pending_inst")
        d["parser_version"] = PARSER_VERSION
        return d


def _num(s) -> float:
    s = (s or "").replace("\n", "").replace(",", "").replace(" ", "").replace("%", "").strip()
    if s in ("", "-", "--", "—"):
        return 0.0
    return float(s)


def _clean(s) -> str:
    return (s or "").replace("\n", "").replace(" ", "").strip()


_NUM_RE = re.compile(r"^-?[\d,\n]+(\.\d+)?%?$|^[-—]+$")
_INTERVAL_RE = re.compile(r"\d{8}-\s*\d{8}")


_PDFIUM_LOCK = threading.Lock()  # pdfium is not thread-safe; concurrent calls crash (realloc invalid next size)


def _locate_pages(pdf_bytes: bytes, keys: list[str]) -> list[int]:
    with _PDFIUM_LOCK:
        return _locate_pages_unlocked(pdf_bytes, keys)


def _locate_pages_unlocked(pdf_bytes: bytes, keys: list[str]) -> list[int]:
    doc = pypdfium2.PdfDocument(pdf_bytes)
    hits = []
    for i in range(len(doc)):
        tp = doc[i].get_textpage()
        txt = tp.get_text_range().replace(" ", "")
        tp.close()
        # skip table-of-contents pages (long runs of dots)
        if any(k in txt for k in keys) and "……" not in txt and "....." not in txt:
            hits.append(i)
    doc.close()
    return hits


def parse_holder_tables(pdf_bytes: bytes) -> HolderTables:
    out = HolderTables()
    pages = _locate_pages(pdf_bytes, ["前十名持有人", "达到或超过20%", "本报告期期末基金份额总额", "持有人结构"])
    if not pages:
        return out
    # tables can span pages: include the page after each hit
    pages = sorted({p for i in pages for p in (i, i + 1)})
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i in pages:
            if i >= len(pdf.pages):
                continue
            for tb in pdf.pages[i].extract_tables():
                _parse_table(tb, out)
    return out


def _inst_from_rows(tb: list[list]) -> float | None:
    """Holder-structure data row: holders, average holding, institutional units, institutional share, individual units ...; take the 3rd number."""
    for row in tb:
        texts = [_clean(c) for c in row if c not in (None, "")]
        nums = [t for t in texts if _NUM_RE.match(t)]
        if len(nums) >= 6 and texts and _NUM_RE.match(texts[0]):
            return _num(nums[2])
    return None


def _parse_table(tb: list[list], out: HolderTables) -> None:
    flat = " ".join(_clean(c) for row in tb for c in row if c)
    if out.pending_inst:  # the previous page had only the header
        inst = _inst_from_rows(tb)
        if inst is not None:
            out.inst_shares, out.pending_inst = inst, False
            return
    # unit-change table (contains "期初", so check it before the >=20% table)
    if "本报告期期末基金份额总额" in flat:
        for row in tb:
            cells = [_clean(c) for c in row if c]
            if len(cells) >= 2 and "本报告期期末基金份额总额" in cells[0] and _NUM_RE.match(cells[-1]):
                out.total_shares = _num(cells[-1])
        return
    # holder structure: institutions / individuals (/ feeder funds); numbers are holders, average, institutional units, share, individual units ...
    if "机构投资者" in flat and "个人投资者" in flat:
        out.inst_shares = _inst_from_rows(tb)
        out.pending_inst = out.inst_shares is None
        return
    # top-ten holders: the header contains "持有人名称" (holder name)
    if "持有人名称" in flat:
        for row in tb:
            cells = [c for c in row if c not in (None, "")]
            if len(cells) >= 4 and _clean(cells[0]).isdigit() and _NUM_RE.match(_clean(cells[-2]) or "x"):
                out.top10.append({"rank": int(_clean(cells[0])), "name": _clean(cells[1]),
                                  "shares": _num(cells[-2]), "pct": _num(cells[-1])})
        return
    # >=20% table: rows contain a YYYYMMDD-YYYYMMDD interval
    if "期初" in flat or any(_INTERVAL_RE.search(_clean(c)) for row in tb for c in row if c):
        inv_type = ""
        for row in tb:
            cells = [c for c in row if c not in (None, "")]
            texts = [_clean(c) for c in cells]
            iv = next((k for k, t in enumerate(texts) if _INTERVAL_RE.search(t)), None)
            if texts and texts[0] in ("机构", "个人"):
                inv_type = texts[0]
            if iv is None:
                continue
            nums = [t for t in texts[iv + 1:] if _NUM_RE.match(t)]
            if len(nums) < 5:
                continue
            seq = next((t for t in texts[:iv] if t.isdigit()), "")
            out.big.append({"seq": seq, "investor_type": inv_type or "机构", "interval": texts[iv],
                            "begin": _num(nums[0]), "buy": _num(nums[1]), "sell": _num(nums[2]),
                            "end": _num(nums[3]), "pct": _num(nums[4])})
