"""Optional OCR through a locally installed Tesseract engine (nothing leaves the PC)."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass

_custom_path: str | None = None


def set_tesseract_path(path: str | None):
    global _custom_path
    _custom_path = path or None


def find_tesseract() -> str | None:
    cands = [_custom_path, os.environ.get("TESSERACT_CMD"), shutil.which("tesseract"),
             os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tesseract", "tesseract.exe"),
             os.path.join(os.path.dirname(sys.executable), "tesseract", "tesseract.exe"),
             r"C:\Program Files\Tesseract-OCR\tesseract.exe",
             r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
             os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def available() -> bool:
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return find_tesseract() is not None


@dataclass
class Word:
    text: str
    box: tuple[float, float, float, float]  # x0, y0, x1, y1
    line: tuple


def ocr_words(image) -> list[Word]:
    """Run Tesseract on a PIL image, returning words with pixel boxes."""
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = find_tesseract()
    d = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config="--psm 3")
    words = []
    for i, txt in enumerate(d["text"]):
        if not txt or not txt.strip():
            continue
        try:
            if float(d["conf"][i]) < 0:
                continue
        except ValueError:
            pass
        x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
        words.append(Word(txt, (x, y, x + w, y + h), (d["page_num"][i], d["block_num"][i], d["par_num"][i], d["line_num"][i])))
    return words


def words_to_text(words: list[Word]) -> tuple[str, list[tuple[int, int]]]:
    """Join words into text (spaces within a line, newlines between lines)
    and return each word's (start, end) offset."""
    parts, offs, pos, prev = [], [], 0, None
    for w in words:
        if prev is not None:
            sep = " " if w.line == prev else "\n"
            parts.append(sep)
            pos += 1
        offs.append((pos, pos + len(w.text)))
        parts.append(w.text)
        pos += len(w.text)
        prev = w.line
    return "".join(parts), offs


def plan_boxes(words: list[Word], replacer) -> list[tuple[tuple, str]]:
    """Match sensitive text against positioned words.  Returns a list of
    (box, new_text) - one box per line touched by a match."""
    text, offs = words_to_text(words)
    out = []
    for s, e, repl, _k in replacer.matches(text):
        idx = [i for i, (a, b) in enumerate(offs) if a < e and b > s]
        if not idx:
            continue
        by_line: dict = {}
        for i in idx:
            by_line.setdefault(words[i].line, []).append(i)
        first = True
        for line, ids in by_line.items():
            a, b = offs[ids[0]][0], offs[ids[-1]][1]
            if first:
                new = text[a:s] + repl + text[e:b] if s >= a else repl + text[e:b]
                first = False
            else:
                new = text[e:b] if e < b and e > a else ""
            boxes = [words[i].box for i in ids]
            box = (min(x[0] for x in boxes), min(x[1] for x in boxes), max(x[2] for x in boxes), max(x[3] for x in boxes))
            out.append((box, new))
        replacer.counts[_k] += 1
    return out
