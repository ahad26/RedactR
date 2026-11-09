"""Word (.docx/.docm), Excel (.xlsx/.xlsm) and PowerPoint (.pptx/.pptm) handling.

These formats are ZIP packages of XML parts.  Working directly on the XML lets
ЯedactR keep every bit of formatting, images and charts intact while still
reaching text that libraries usually miss: headers/footers, footnotes, comments,
tracked-change authors, text boxes, SmartArt, chart labels, pivot caches,
hyperlink targets, document properties and embedded Office files.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field

from lxml import etree

from .hints import table_hints

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_X = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

TEXT_TAGS = {"t", "delText", "instrText"}
PARA_TAGS = {"p", "si", "is", "text", "comment"}           # w:p, a:p, x:si, x:is, x:text (comment body)
AUTHOR_ATTRS = {"author", "initials", "displayName", "userId", "providerId"}
DESC_ATTRS = {"descr", "title"}
# human-entered document properties (dates, versions, counts are left alone)
META_FIELDS = {"title", "subject", "creator", "keywords", "description", "lastModifiedBy", "category",
               "contentStatus", "identifier", "Company", "Manager", "HyperlinkBase", "lpstr", "lpwstr"}
OFFICE_EXT = (".docx", ".docm", ".xlsx", ".xlsm", ".pptx", ".pptm", ".dotx", ".potx", ".xltx")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".emf", ".wmf")
SHEET_BAD = re.compile(r"[\[\]:*?/\\]")


def _local(tag) -> str:
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _is_xml(name: str) -> bool:
    return name.endswith(".xml") or name.endswith(".rels") or name.endswith(".vml")


@dataclass
class OfficeResult:
    texts: list[tuple[str, str]] = field(default_factory=list)          # (location, text)
    forced: list[tuple[str, str, str]] = field(default_factory=list)    # (value, category, location)
    notes: list[str] = field(default_factory=list)
    images: int = 0


# =============================================================================== reading
def _para_groups(root):
    """Yield lists of text elements that belong to the same paragraph."""
    # keyed by the lxml element itself (ids of lxml proxies can be reused, elements cannot)
    groups: dict = {}
    for el in root.iter():
        if _local(el.tag) not in TEXT_TAGS:
            continue
        anc = el.getparent()
        while anc is not None and _local(anc.tag) not in PARA_TAGS:
            anc = anc.getparent()
        key = anc if anc is not None else el.getparent()
        groups.setdefault(key, []).append(el)
    return list(groups.values())


def _tables(root, kind: str) -> list[list[list[str]]]:
    """Return tables as rows of cell text for Word (w:tbl) and PowerPoint (a:tbl)."""
    out = []
    for tbl in root.iter():
        if _local(tbl.tag) != "tbl":
            continue
        rows = []
        for tr in tbl:
            if _local(tr.tag) != "tr":
                continue
            row = []
            for tc in tr:
                if _local(tc.tag) != "tc":
                    continue
                row.append("".join(t.text or "" for t in tc.iter() if _local(t.tag) == "t").strip())
            rows.append(row)
        out.append(rows)
    return out


def extract_office(path_or_bytes, label: str = "") -> OfficeResult:
    res = OfficeResult()
    data = path_or_bytes if isinstance(path_or_bytes, bytes) else open(path_or_bytes, "rb").read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        shared = []
        if "xl/sharedStrings.xml" in names:
            root = etree.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root:
                shared.append("".join(t.text or "" for t in si.iter() if _local(t.tag) == "t"))
        for name in names:
            low = name.lower()
            if low.endswith(IMAGE_EXT) and "/media/" in low:
                res.images += 1
                continue
            if low.endswith(OFFICE_EXT) and "embeddings" in low:
                sub = extract_office(z.read(name), f"{label}>{name}")
                res.texts += sub.texts
                res.forced += sub.forced
                res.images += sub.images
                continue
            if not _is_xml(name):
                if "embeddings" in low:
                    res.notes.append(f"Embedded object '{name}' could not be inspected.")
                continue
            try:
                root = etree.fromstring(z.read(name))
            except etree.XMLSyntaxError:
                continue
            loc = f"{label}:{name}" if label else name
            chunks = []
            for g in _para_groups(root):
                chunks.append("".join(e.text or "" for e in g))
            for el in root.iter():
                ln = _local(el.tag)
                if ln == "v" and el.text and not _numeric(el.text) and "chart" in low:
                    chunks.append(el.text)
                if ln in ("oddHeader", "evenHeader", "firstHeader", "oddFooter", "evenFooter", "firstFooter") and el.text:
                    chunks.append(re.sub(r"&[A-Z\"]?", " ", el.text))
                if name.startswith("docProps/") and el.text and len(el) == 0 and ln in META_FIELDS:
                    chunks.append(el.text)
                for a, v in el.attrib.items():
                    la = _local(a)
                    if la in AUTHOR_ATTRS or la in DESC_ATTRS:
                        chunks.append(v)
                    elif la == "name" and (ln in ("sheet", "tableColumn", "cmAuthor", "person") or "commentAuthors" in name):
                        chunks.append(v)
                    elif la == "v" and ln == "s" and "pivotCache" in name:
                        chunks.append(v)
                    elif la == "Target" and el.get("TargetMode") == "External":
                        chunks.append(v)
            text = "\n".join(c for c in chunks if c and c.strip())
            if text:
                res.texts.append((loc, text))
            # the document's own "Company" property names the organisation
            if low == "docprops/app.xml":
                for el in root.iter():
                    if _local(el.tag) == "Company" and el.text and el.text.strip():
                        res.forced.append((el.text.strip(), "ORG", loc))
            # table hints
            if low.startswith("word/") or low.startswith("ppt/"):
                for rows in _tables(root, "w"):
                    res.forced += table_hints(rows, loc)
            if re.match(r"xl/worksheets/sheet\d+\.xml", low):
                rows = _sheet_rows(root, shared)
                res.forced += table_hints(rows, loc)
                nums = [v for r in rows for v in r if v and _numeric(v)]
                if nums:
                    res.texts.append((loc + "#numbers", "\n".join(nums)))
    return res


def _numeric(s: str) -> bool:
    return bool(re.fullmatch(r"\s*-?\d+(?:\.\d+)?(?:E[-+]?\d+)?\s*", s or "", re.I))


def _col_index(ref: str) -> int:
    letters = re.match(r"[A-Z]+", ref or "A")
    n = 0
    for ch in letters.group(0):
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _sheet_rows(root, shared: list[str]) -> list[list[str]]:
    rows = []
    for row in root.iter(f"{{{NS_X}}}row"):
        cells: dict[int, str] = {}
        for c in row.iter(f"{{{NS_X}}}c"):
            t = c.get("t")
            v = c.find(f"{{{NS_X}}}v")
            val = ""
            if t == "s" and v is not None and v.text and v.text.isdigit():
                idx = int(v.text)
                val = shared[idx] if idx < len(shared) else ""
            elif t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(f"{{{NS_X}}}t"))
            elif v is not None and v.text:
                val = v.text
            cells[_col_index(c.get("r", "A"))] = val
        if cells:
            width = max(cells) + 1
            rows.append([cells.get(i, "") for i in range(width)])
    return rows


# =============================================================================== writing
@dataclass
class WriteStats:
    notes: list[str] = field(default_factory=list)
    numeric_cells: int = 0


def process_office(data: bytes, replacer, strip_metadata: bool, numeric: bool, restore: bool = False,
                   stats: WriteStats | None = None) -> bytes:
    """Return a new package with every text replaced through `replacer`."""
    stats = stats or WriteStats()
    src = zipfile.ZipFile(io.BytesIO(data))
    out_buf = io.BytesIO()
    names = src.namelist()

    # Excel: rename sheets first so formulas can be fixed consistently
    sheet_renames: dict[str, str] = {}
    if "xl/workbook.xml" in names:
        wb = etree.fromstring(src.read("xl/workbook.xml"))
        used = set()
        for sh in wb.iter(f"{{{NS_X}}}sheet"):
            old = sh.get("name")
            new = SHEET_BAD.sub("", replacer.sub(old))[:31].strip() or "Sheet"
            base, i = new, 2
            while new.lower() in used:
                new = f"{base[:28]}_{i}"
                i += 1
            used.add(new.lower())
            if new != old:
                sheet_renames[old] = new

    with zipfile.ZipFile(out_buf, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            name = info.filename
            raw = src.read(name)
            low = name.lower()
            if low.endswith(OFFICE_EXT) and "embeddings" in low:
                try:
                    raw = process_office(raw, replacer, strip_metadata, numeric, restore, stats)
                except Exception as exc:  # keep going, but tell the user
                    stats.notes.append(f"Embedded file {name} could not be processed: {exc}")
            elif _is_xml(name):
                try:
                    raw = _process_part(name, raw, replacer, strip_metadata, numeric, restore, sheet_renames, stats)
                except etree.XMLSyntaxError:
                    pass
            dst.writestr(info, raw)
    return out_buf.getvalue()


def _set_text(el, value: str):
    el.text = value
    if _local(el.tag) in ("t", "delText", "instrText") and el.tag.startswith(f"{{{NS_W}}}") or \
            el.tag.startswith(f"{{{NS_X}}}"):
        if value != value.strip():
            el.set(XML_SPACE, "preserve")


def _fix_formula(text: str, replacer, sheet_renames: dict[str, str]) -> str:
    for old, new in sheet_renames.items():
        q_new = f"'{new}'" if re.search(r"[^A-Za-z0-9_]", new) else new
        text = text.replace(f"'{old}'!", f"{q_new}!")
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", old):
            text = re.sub(r"(?<![\w'])" + re.escape(old) + "!", q_new + "!", text)
    # string literals inside formulas
    return re.sub(r'"([^"]*)"', lambda m: '"' + replacer.sub(m.group(1)) + '"', text)


def _process_part(name, raw, replacer, strip_metadata, numeric, restore, sheet_renames, stats) -> bytes:
    root = etree.fromstring(raw)
    low = name.lower()
    changed = False

    # paragraphs / runs
    for g in _para_groups(root):
        segs = [e.text or "" for e in g]
        new = replacer.sub_segments(segs)
        if new != segs:
            changed = True
            for e, t in zip(g, new):
                if (e.text or "") != t:
                    _set_text(e, t)

    is_sheet = bool(re.match(r"xl/worksheets/sheet\d+\.xml", low))
    is_core = low == "docprops/core.xml"
    is_app = low == "docprops/app.xml"

    for el in list(root.iter()):
        if not isinstance(el.tag, str):
            continue
        ln = _local(el.tag)
        # ---- attributes
        for a, v in list(el.attrib.items()):
            la = _local(a)
            nv = v
            if la in AUTHOR_ATTRS:
                nv = "Author" if (strip_metadata and not restore and la in ("author", "displayName")) else \
                     ("A" if strip_metadata and not restore and la == "initials" else replacer.sub(v))
                if strip_metadata and not restore and la in ("userId", "providerId"):
                    nv = ""
            elif la in DESC_ATTRS:
                nv = replacer.sub(v)
            elif la == "name" and ln == "sheet" and low == "xl/workbook.xml":
                nv = sheet_renames.get(v, v)
            elif la == "name" and (ln in ("tableColumn", "cmAuthor", "person") or "commentauthors" in low):
                nv = replacer.sub(v)
            elif la == "v" and ln == "s" and "pivotcache" in low:
                nv = replacer.sub(v)
            elif la == "Target" and el.get("TargetMode") == "External":
                nv = replacer.sub(v)
            if nv != v:
                el.set(a, nv)
                changed = True
        # ---- element text that is not inside a run
        txt = el.text
        if not txt:
            continue
        nt = txt
        if ln == "f" or (ln == "definedName"):
            nt = _fix_formula(txt, replacer, sheet_renames)
        elif ln in ("oddHeader", "evenHeader", "firstHeader", "oddFooter", "evenFooter", "firstFooter"):
            nt = replacer.sub(txt)
        elif ln == "v" and "chart" in low and not _numeric(txt):
            nt = replacer.sub(txt)
        elif ln == "v" and is_sheet:
            c = el.getparent()
            t = c.get("t") if c is not None else None
            if t == "str":
                nt = replacer.sub(txt)
            elif numeric and _numeric(txt) and c.find(f"{{{NS_X}}}f") is not None:
                if replacer.sub(txt.strip()) != txt.strip():
                    c.remove(el)  # drop the cached sensitive result; Excel recalculates on open
                    changed = True
                    continue
            elif (t in (None, "n")) and numeric and _numeric(txt) and c.find(f"{{{NS_X}}}f") is None:
                rep = replacer.sub(txt.strip())
                if rep != txt.strip() and not _numeric(rep):
                    # turn the number into a text cell holding the placeholder
                    c.remove(el)
                    c.set("t", "inlineStr")
                    is_el = etree.SubElement(c, f"{{{NS_X}}}is")
                    t_el = etree.SubElement(is_el, f"{{{NS_X}}}t")
                    t_el.text = rep
                    stats.numeric_cells += 1
                    changed = True
                    continue
        elif ln == "t" and is_sheet and restore:
            pass
        elif is_core:
            if ln not in META_FIELDS:
                pass
            elif strip_metadata and not restore and ln in ("creator", "lastModifiedBy", "description", "keywords",
                                                           "category", "contentStatus", "identifier"):
                nt = ""
            else:
                nt = replacer.sub(txt)
        elif is_app:
            if strip_metadata and not restore and ln in ("Company", "Manager", "HyperlinkBase"):
                nt = ""
            elif ln == "lpstr":
                nt = sheet_renames.get(txt, replacer.sub(txt))
            elif ln in ("Company", "Manager"):
                nt = replacer.sub(txt)
        elif low == "docprops/custom.xml" and len(el) == 0 and ln in META_FIELDS:
            nt = "" if strip_metadata and not restore else replacer.sub(txt)
        if nt != txt:
            el.text = nt
            changed = True

    # restoring numbers: a restored inline string that is a plain number becomes a number again
    if restore and is_sheet:
        for c in root.iter(f"{{{NS_X}}}c"):
            if c.get("t") == "inlineStr":
                txt = "".join(x.text or "" for x in c.iter(f"{{{NS_X}}}t"))
                if _numeric(txt):
                    for ch in list(c):
                        if _local(ch.tag) == "is":
                            c.remove(ch)
                    c.attrib.pop("t", None)
                    v = etree.SubElement(c, f"{{{NS_X}}}v")
                    v.text = txt.strip()
                    changed = True

    if is_sheet and stats.numeric_cells and not restore:
        pass
    if low == "xl/workbook.xml" and numeric and not restore:
        # cached formula results may hold sensitive numbers: ask Excel to recalculate
        calc = root.find(f"{{{NS_X}}}calcPr")
        if calc is not None:
            calc.set("fullCalcOnLoad", "1")
            changed = True

    if not changed:
        return raw
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
