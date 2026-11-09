"""File-type dispatch: extract text for scanning and write sanitized / restored copies."""

from __future__ import annotations

import csv
import io
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

from . import ocr
from .hints import table_hints
from .ooxml import OFFICE_EXT, WriteStats, extract_office, process_office

TEXT_EXT = (".txt", ".md", ".csv", ".tsv", ".json", ".xml", ".html", ".htm", ".log", ".yaml", ".yml", ".ini",
            ".sql", ".eml", ".rtf_txt")
IMG_EXT = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".gif", ".webp")
PDF_EXT = (".pdf",)
LEGACY_EXT = {".doc": "docx", ".rtf": "docx", ".odt": "docx", ".xls": "xlsx", ".ods": "xlsx",
              ".ppt": "pptx", ".odp": "pptx"}
SUPPORTED = OFFICE_EXT + TEXT_EXT + IMG_EXT + PDF_EXT + tuple(LEGACY_EXT)

FILE_DIALOG_TYPES = [
    ("All supported", " ".join("*" + e for e in SUPPORTED)),
    ("Word", "*.docx *.docm *.doc *.rtf *.odt"),
    ("Excel", "*.xlsx *.xlsm *.xls *.csv *.ods"),
    ("PowerPoint", "*.pptx *.pptm *.ppt *.odp"),
    ("PDF", "*.pdf"),
    ("Images (OCR)", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.gif *.webp"),
    ("Text", "*.txt *.md *.json *.xml *.html *.log *.eml"),
    ("All files", "*.*"),
]


@dataclass
class Extracted:
    texts: list[tuple[str, str]] = field(default_factory=list)
    forced: list[tuple[str, str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    work_path: str = ""   # path actually processed (after legacy conversion)


def ext_of(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def is_supported(path: str) -> bool:
    return ext_of(path) in SUPPORTED


# ============================================================================ legacy
def _find_soffice() -> str | None:
    for c in [shutil.which("soffice"), r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"]:
        if c and os.path.isfile(c):
            return c
    return None


_PS_CONVERT = {
    "docx": "$a=New-Object -ComObject Word.Application;$a.Visible=$false;$d=$a.Documents.Open('{src}',$false,$true);"
            "$d.SaveAs2('{dst}',16);$d.Close($false);$a.Quit()",
    "xlsx": "$a=New-Object -ComObject Excel.Application;$a.Visible=$false;$a.DisplayAlerts=$false;"
            "$w=$a.Workbooks.Open('{src}',0,$true);$w.SaveAs('{dst}',51);$w.Close($false);$a.Quit()",
    "pptx": "$a=New-Object -ComObject PowerPoint.Application;$p=$a.Presentations.Open('{src}',$true,$false,$false);"
            "$p.SaveAs('{dst}',24);$p.Close();$a.Quit()",
}


def convert_legacy(path: str) -> str:
    """Convert .doc/.xls/.ppt/.rtf/.od* to the modern format using LibreOffice or MS Office (local)."""
    target = LEGACY_EXT[ext_of(path)]
    tmp = tempfile.mkdtemp(prefix="redactr_")
    stem = os.path.splitext(os.path.basename(path))[0]
    dst = os.path.join(tmp, f"{stem}.{target}")
    soffice = _find_soffice()
    if soffice:
        subprocess.run([soffice, "--headless", "--convert-to", target, "--outdir", tmp, path],
                       capture_output=True, timeout=180)
        if os.path.isfile(dst):
            return dst
    if os.name == "nt":
        cmd = _PS_CONVERT[target].format(src=os.path.abspath(path).replace("'", "''"), dst=dst.replace("'", "''"))
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                       capture_output=True, timeout=300, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if os.path.isfile(dst):
            return dst
    raise RuntimeError(f"Cannot open {ext_of(path)} files: install Microsoft Office or LibreOffice, "
                       f"or save the file as .{target} first.")


# ============================================================================ text files
def _read_text(path: str) -> tuple[str, str]:
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            if enc == "utf-16" and not raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
                continue
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8"


# ============================================================================ PDF
def _pdf_page_words(page, use_ocr: bool):
    """Return (words, scale, is_ocr) for one PDF page."""
    raw = page.get_text("words")
    words = [ocr.Word(w[4], (w[0], w[1], w[2], w[3]), (w[5], w[6])) for w in raw]
    if len(words) < 3 and page.get_images() and use_ocr and ocr.available():
        from PIL import Image
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        ow = ocr.ocr_words(img)
        s = 72 / 300
        return [ocr.Word(w.text, tuple(v * s for v in w.box), w.line) for w in ow], True
    return words, False


def _pdf_extract(path: str, ex: Extracted, use_ocr: bool):
    import pymupdf as fitz
    doc = fitz.open(path)
    scanned_no_ocr = 0
    for i, page in enumerate(doc):
        words, was_ocr = _pdf_page_words(page, use_ocr)
        if not words and page.get_images():
            scanned_no_ocr += 1
        text, _ = ocr.words_to_text(words)
        ex.texts.append((f"page {i + 1}" + (" (OCR)" if was_ocr else ""), text))
    meta = "\n".join(v for k, v in (doc.metadata or {}).items()
                     if v and k in ("title", "author", "subject", "keywords", "creator"))
    if meta:
        ex.texts.append(("metadata", meta))
    toc = "\n".join(t[1] for t in doc.get_toc())
    if toc:
        ex.texts.append(("bookmarks", toc))
    if scanned_no_ocr:
        ex.notes.append(f"{scanned_no_ocr} scanned page(s) could not be read - install Tesseract OCR.")
    doc.close()


def _fit_text(fitz, text, box):
    w, h = box[2] - box[0], box[3] - box[1]
    fs = max(3.0, min(h * 0.75, 14))
    tl = fitz.get_text_length(text, fontname="helv", fontsize=fs)
    if tl > w and tl > 0:
        fs = max(3.0, fs * w / tl)   # shrink to fit so neighbouring words stay readable
    return fs


def _base14(fontname: str, flags: int) -> str:
    f = (fontname or "").lower()
    bold, italic = bool(flags & 16) or "bold" in f, bool(flags & 2) or "italic" in f or "oblique" in f
    if "courier" in f or "mono" in f or flags & 8:
        fam = ("cour", "cobo", "coit", "cobi")
    elif "times" in f or "serif" in f and "sans" not in f or "georgia" in f or "garamond" in f or flags & 4:
        fam = ("tiro", "tibo", "tiit", "tibi")
    else:
        fam = ("helv", "hebo", "heit", "hebi")
    return fam[(1 if bold else 0) + (2 if italic else 0)]


def _pdf_rewrite_page(fitz, page, replacer):
    """Rewrite all text of a page in reading order with replacements applied.
    Returns None when the page cannot be rewritten (non-Latin text), False when
    nothing changed, True when rewritten."""
    d = page.get_text("dict")
    lines = []
    for b in d.get("blocks", []):
        if b.get("type") != 0:
            continue
        for ln in b.get("lines", []):
            spans = [s for s in ln.get("spans", []) if s.get("text")]
            if spans:
                lines.append((ln, spans))
    if any(ord(c) > 255 for _, sp in lines for s in sp for c in s["text"]):
        return None
    planned, changed = [], False
    for ln, spans in lines:
        segs = [s["text"] for s in spans]
        new = replacer.sub_segments(segs)
        changed |= new != segs
        planned.append((ln, spans, new))
    if not changed:
        return False
    page.add_redact_annot(page.rect)
    kw = {"images": fitz.PDF_REDACT_IMAGE_NONE}
    if hasattr(fitz, "PDF_REDACT_LINE_ART_NONE"):
        kw["graphics"] = fitz.PDF_REDACT_LINE_ART_NONE
    page.apply_redactions(**kw)
    rot_map = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}
    for ln, spans, new in planned:
        rot = rot_map.get(tuple(round(v) for v in ln.get("dir", (1, 0))), 0)
        for s, t in zip(spans, new):
            if not t.strip():
                continue
            font = _base14(s.get("font", ""), s.get("flags", 0))
            fs = s["size"]
            w = (s["bbox"][2] - s["bbox"][0]) if rot in (0, 180) else (s["bbox"][3] - s["bbox"][1])
            tl = fitz.get_text_length(t, fontname=font, fontsize=fs)
            if w > 0 and tl > w * 1.02:
                fs = max(3.0, fs * w / tl)
            c = s.get("color", 0)
            rgb = ((c >> 16) & 255) / 255, ((c >> 8) & 255) / 255, (c & 255) / 255
            page.insert_text(s["origin"], t, fontsize=fs, fontname=font, color=rgb, rotate=rot)
    return True


def _pdf_ocr_page(fitz, page, words, replacer):
    """Scanned page: blank the sensitive words in the image, draw the replacements, and add an
    invisible text layer (in reading order) so AI tools can read the sanitized page as text."""
    lines: dict = {}
    for w in words:
        lines.setdefault(w.line, []).append(w)
    redacts, draws = [], []  # draws: (box, text, visible)
    for lw in lines.values():
        n = len(lw)
        segs = [w.text + (" " if i < n - 1 else "") for i, w in enumerate(lw)]
        new = replacer.sub_segments(segs)
        i = 0
        while i < n:
            if new[i] == segs[i]:
                draws.append((lw[i].box, segs[i], False))
                i += 1
                continue
            j = i + 1
            while j < n and new[j] != segs[j]:
                j += 1  # every word touched by the same replacement shares one box
            bx = [lw[k].box for k in range(i, j)]
            box = (min(b[0] for b in bx), min(b[1] for b in bx), max(b[2] for b in bx), max(b[3] for b in bx))
            redacts.append(box)
            text = "".join(new[i:j]).strip()
            if text:
                draws.append((box, text + (" " if segs[j - 1].endswith(" ") else ""), True))
            i = j
    if not redacts:
        return False
    for b in redacts:
        h = b[3] - b[1]
        # grow the box a little so no edge of the original glyphs survives in the image
        page.add_redact_annot(fitz.Rect(b[0] - 1.2, b[1] - h * 0.18, b[2] + 1.2, b[3] + h * 0.18), fill=(1, 1, 1))
    kw = {"images": fitz.PDF_REDACT_IMAGE_PIXELS}
    if hasattr(fitz, "PDF_REDACT_LINE_ART_NONE"):
        kw["graphics"] = fitz.PDF_REDACT_LINE_ART_NONE
    page.apply_redactions(**kw)
    for box, text, visible in draws:
        w, h = box[2] - box[0], box[3] - box[1]
        if w <= 0 or h <= 0:
            continue
        fs = max(3.0, h * (0.95 if visible else 1.0))
        tl = fitz.get_text_length(text.rstrip(), fontname="helv", fontsize=fs)
        limit = w
        if tl > limit:
            fs = max(3.0, fs * limit / tl)
        page.insert_text((box[0], box[3] - h * 0.18), text, fontsize=fs, fontname="helv",
                         color=(0, 0, 0), render_mode=0 if visible else 3)
    return True


def _pdf_write(path: str, out: str, replacer, strip_metadata: bool, use_ocr: bool, restore: bool = False):
    import pymupdf as fitz
    doc = fitz.open(path)
    for page in doc:
        # hyperlinks
        for link in page.get_links():
            uri = link.get("uri")
            if uri:
                nu = replacer.sub(uri)
                if nu != uri:
                    link["uri"] = nu
                    page.update_link(link)
        words, was_ocr = _pdf_page_words(page, use_ocr)
        if was_ocr:
            _pdf_ocr_page(fitz, page, words, replacer)
            continue
        done = _pdf_rewrite_page(fitz, page, replacer)
        if done is not None:
            continue
        plan = ocr.plan_boxes(words, replacer)
        if not plan:
            continue
        for box, _new in plan:
            h = box[3] - box[1]
            # slightly inset so characters of neighbouring words are not caught
            page.add_redact_annot(fitz.Rect(box[0] + 0.6, box[1] + h * 0.2, box[2] - 0.6, box[3] - h * 0.2),
                                  fill=(1, 1, 1))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS if was_ocr else fitz.PDF_REDACT_IMAGE_NONE,
                              graphics=fitz.PDF_REDACT_LINE_ART_NONE if hasattr(fitz, "PDF_REDACT_LINE_ART_NONE") else 0)
        for box, new in plan:
            if not new:
                continue
            fs = _fit_text(fitz, new, box)
            h = box[3] - box[1]
            page.insert_text((box[0], box[3] - max(1.0, (h - fs) / 2) - fs * 0.15), new,
                             fontsize=fs, fontname="helv", color=(0, 0, 0))
    # metadata & bookmarks
    md = doc.metadata or {}
    if strip_metadata and not restore:
        doc.set_metadata({})
        try:
            doc.del_xml_metadata()
        except Exception:
            pass
    else:
        doc.set_metadata({k: replacer.sub(v) if isinstance(v, str) else v for k, v in md.items()
                          if k in ("title", "author", "subject", "keywords", "creator", "producer")})
    toc = doc.get_toc(simple=False)
    if toc:
        doc.set_toc([[t[0], replacer.sub(t[1])] + list(t[2:]) for t in toc])
    doc.save(out, garbage=4, deflate=True, clean=True)
    doc.close()


# ============================================================================ images
def _image_extract(path: str, ex: Extracted):
    if not ocr.available():
        ex.notes.append("Image skipped - Tesseract OCR is not installed (see Settings).")
        return
    from PIL import Image
    img = Image.open(path)
    img.load()
    words = ocr.ocr_words(img.convert("RGB"))
    text, _ = ocr.words_to_text(words)
    ex.texts.append(("ocr", text))


def _load_font(size):
    from PIL import ImageFont
    for f in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _image_write(path: str, out: str, replacer) -> str:
    from PIL import Image, ImageDraw
    img = Image.open(path)
    img.load()
    rgb = img.convert("RGB")
    words = ocr.ocr_words(rgb)
    text, _ = ocr.words_to_text(words)
    plan = ocr.plan_boxes(words, replacer)
    draw = ImageDraw.Draw(rgb)
    for box, new in plan:
        x0, y0, x1, y1 = [int(v) for v in box]
        draw.rectangle([x0 - 2, y0 - 2, x1 + 2, y1 + 2], fill=(255, 255, 255))
        if new:
            size = max(8, int((y1 - y0) * 0.9))
            font = _load_font(size)
            while size > 8 and draw.textlength(new, font=font) > (x1 - x0) * 1.3:
                size -= 1
                font = _load_font(size)
            draw.text((x0, y0), new, fill=(0, 0, 0), font=font)
    fmt = {".jpg": "JPEG", ".jpeg": "JPEG"}.get(ext_of(out))
    if fmt == "JPEG":
        rgb.save(out, fmt, quality=95)  # saved without EXIF/GPS metadata
    else:
        rgb.save(out)
    # also give a clean text version of what the image says
    txt_out = os.path.splitext(out)[0] + ".txt"
    with open(txt_out, "w", encoding="utf-8") as fh:
        fh.write(replacer.sub(text))
    return txt_out


# ============================================================================ public API
def extract(path: str, use_ocr: bool = True) -> Extracted:
    ex = Extracted(work_path=path)
    e = ext_of(path)
    if e in LEGACY_EXT:
        ex.work_path = convert_legacy(path)
        ex.notes.append(f"Converted {e} to .{LEGACY_EXT[e]} locally.")
        e = ext_of(ex.work_path)
    p = ex.work_path
    if e in OFFICE_EXT:
        r = extract_office(p)
        ex.texts, ex.forced = r.texts, r.forced
        ex.notes += r.notes
        if r.images:
            msg = f"{r.images} embedded image(s) found - text inside pictures is not changed."
            ex.notes.append(msg)
    elif e in PDF_EXT:
        _pdf_extract(p, ex, use_ocr)
    elif e in IMG_EXT:
        _image_extract(p, ex)
    elif e in TEXT_EXT:
        text, _ = _read_text(p)
        ex.texts.append(("text", text))
        if e in (".csv", ".tsv"):
            rows = list(csv.reader(io.StringIO(text), delimiter="\t" if e == ".tsv" else ","))
            ex.forced += table_hints(rows[:5000], "csv")
    else:
        raise RuntimeError(f"Unsupported file type: {e}")
    return ex


def output_name(src: str, work_path: str, suffix: str) -> str:
    stem = os.path.splitext(os.path.basename(src))[0]
    return f"{stem}_{suffix}{ext_of(work_path)}"


def write_copy(src: str, work_path: str, out_path: str, replacer, *, strip_metadata: bool, numeric: bool,
               use_ocr: bool = True, restore: bool = False) -> list[str]:
    """Write the sanitized (or restored) copy. Returns notes."""
    notes: list[str] = []
    e = ext_of(work_path)
    if e in OFFICE_EXT:
        stats = WriteStats()
        data = open(work_path, "rb").read()
        new = process_office(data, replacer, strip_metadata, numeric, restore, stats)
        with open(out_path, "wb") as fh:
            fh.write(new)
        notes += stats.notes
        if stats.numeric_cells:
            notes.append(f"{stats.numeric_cells} numeric cell(s) replaced with placeholders.")
    elif e in PDF_EXT:
        _pdf_write(work_path, out_path, replacer, strip_metadata, use_ocr, restore)
    elif e in IMG_EXT:
        if restore:
            raise RuntimeError("Images cannot be restored - restore the AI's text answer instead.")
        if not ocr.available():
            raise RuntimeError("Tesseract OCR is not installed, so images cannot be sanitized.")
        txt = _image_write(work_path, out_path, replacer)
        notes.append(f"Text version written to {os.path.basename(txt)}.")
    elif e in TEXT_EXT:
        text, enc = _read_text(work_path)
        out_enc = "utf-8" if enc in ("utf-8-sig", "latin-1") else enc
        with open(out_path, "w", encoding=out_enc, newline="") as fh:
            fh.write(replacer.sub(text))
    else:
        raise RuntimeError(f"Unsupported file type: {e}")
    return notes


def read_back_text(path: str) -> str:
    """Re-extract text from a written file (used for the leak check)."""
    try:
        ex = extract(path, use_ocr=False)
        return "\n".join(t for _, t in ex.texts)
    except Exception:
        return ""
