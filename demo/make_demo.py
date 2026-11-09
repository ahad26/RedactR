"""Record the ЯedactR demo video  ->  demo/RedactR-demo.mp4

Drives the real desktop app with the sample documents, captures ONLY the app's
own window (PrintWindow, never the screen), and adds captions, before/after
comparisons and title cards.  Run from the repo root:

    .venv\\Scripts\\python samples\\make_samples.py
    .venv\\Scripts\\python demo\\make_demo.py
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import shutil
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
WORK = tempfile.mkdtemp(prefix="redactr_demo_")
os.environ["APPDATA"] = os.path.join(WORK, "appdata")   # keep the user's own settings untouched

ctypes.windll.shcore.SetProcessDpiAwareness(1)

import imageio_ffmpeg  # noqa: E402
import pymupdf  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402
from tkinter import messagebox  # noqa: E402

from redactr import gui  # noqa: E402
from redactr.engine import Sanitizer  # noqa: E402
from redactr.levels import LEVELS_BY_KEY  # noqa: E402
from redactr.project import Project  # noqa: E402
from redactr.vault import Vault  # noqa: E402

OUT = os.path.join(ROOT, "demo", "RedactR-demo.mp4")
SAMPLES = os.path.join(ROOT, "samples", "input")
W, H, FPS = 1920, 1080, 10
MIDNIGHT, DUSK, GOLD, CORAL, INK, MUTED, LINE = ("#312C51", "#48426D", "#F0C38E", "#F1AA9B", "#F7F4FB",
                                                 "#C9C3E3", "#5E5788")

for name in ("showwarning", "showinfo", "showerror"):          # no blocking dialogs while recording
    setattr(messagebox, name, lambda *a, **k: None)


def font(size, bold=False):
    for f in (["seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def mono(size):
    for f in ("consola.ttf", "cour.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return font(size)


# ------------------------------------------------------------------ window capture (app window only)
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG), ("biPlanes", wt.WORD),
                ("biBitCount", wt.WORD), ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG), ("biClrUsed", wt.DWORD),
                ("biClrImportant", wt.DWORD)]


user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32


def grab(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = user32.GetWindowDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    user32.PrintWindow(hwnd, mdc, 2)
    bi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(hwnd, hdc)
    return Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB"), (r.left, r.top)


# ------------------------------------------------------------------ video writer + compositing
class Video:
    def __init__(self, path):
        self.writer = imageio_ffmpeg.write_frames(path, (W, H), fps=FPS, codec="libx264", quality=8,
                                                  pix_fmt_out="yuv420p", macro_block_size=8,
                                                  output_params=["-movflags", "+faststart"])
        self.writer.send(None)
        self.frames = 0
        self.last = None

    def add(self, img: Image.Image, seconds: float = 0.0):
        data = img.convert("RGB").tobytes()
        n = max(1, int(round(seconds * FPS)))
        for _ in range(n):
            self.writer.send(data)
        self.frames += n
        self.last = img

    def close(self):
        self.writer.close()


def base_canvas():
    img = Image.new("RGB", (W, H), MIDNIGHT)
    d = ImageDraw.Draw(img)
    d.text((40, 22), "Я", font=font(30, True), fill=CORAL)
    d.text((40 + d.textlength("Я", font=font(30, True)), 22), "edactR", font=font(30, True), fill=INK)
    t = "Software by Ahad  ·  github.com/ahad26"
    d.text((W - 40 - d.textlength(t, font=font(20)), 30), t, font=font(20), fill=MUTED)
    return img


def caption_bar(img, text, step=None):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([40, H - 108, W - 40, H - 28], radius=22, fill=DUSK)
    x = 70
    if step:
        f = font(24, True)
        tw = d.textlength(step, font=f)
        d.rounded_rectangle([x, H - 88, x + tw + 32, H - 48], radius=20, fill=GOLD)
        d.text((x + 16, H - 84), step, font=f, fill=MIDNIGHT)
        x += tw + 56
    d.text((x, H - 88), text, font=font(30), fill=INK)
    return img


def zoom_box(win_img, view, aspect):
    """A crop of the window around `view` (x, y, w, h) with the given aspect ratio, so text stays readable."""
    vx, vy, vw, vh = view
    cw = max(vw * 1.25, win_img.width * 0.55, vh * 1.25 * aspect)
    cw = min(cw, win_img.width)
    ch = cw / aspect
    if ch < vh * 1.12:                       # tall target: keep all of it, accept side margins
        ch = vh * 1.12
        cw = min(win_img.width, ch * aspect)
    if ch > win_img.height:
        ch = win_img.height
        cw = min(win_img.width, ch * aspect)
    cx, cy = vx + vw / 2, vy + vh / 2
    x0 = min(max(0, cx - cw / 2), win_img.width - cw)
    y0 = min(max(0, cy - ch / 2), win_img.height - ch)
    return int(x0), int(y0), int(x0 + cw), int(y0 + ch)


def compose_app(win_img, caption, step=None, focus=None, view=None):
    """Place the app window on the branded canvas, zoomed on `view`; focus = (x, y, w, h) to highlight."""
    img = base_canvas()
    area_w, area_h = W - 80, H - 80 - 140
    if view:
        x0, y0, x1, y1 = zoom_box(win_img, view, area_w / area_h)
        win_img = win_img.crop((x0, y0, x1, y1))
        if focus:
            focus = (focus[0] - x0, focus[1] - y0, focus[2], focus[3])
    s = min(area_w / win_img.width, area_h / win_img.height)
    shot = win_img.resize((int(win_img.width * s), int(win_img.height * s)), Image.LANCZOS)
    ox, oy = (W - shot.width) // 2, 80 + (area_h - shot.height) // 2
    shadow = Image.new("RGBA", (shot.width + 40, shot.height + 40), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([20, 20, shot.width + 20, shot.height + 20], radius=12, fill=(0, 0, 0, 120))
    img.paste(shadow.filter(ImageFilter.GaussianBlur(14)), (ox - 20, oy - 12), shadow.filter(ImageFilter.GaussianBlur(14)))
    img.paste(shot, (ox, oy))
    d = ImageDraw.Draw(img)
    if focus:
        x, y, w, h = focus
        x0, y0, x1, y1 = ox + x * s - 6, oy + y * s - 6, ox + (x + w) * s + 6, oy + (y + h) * s + 6
        # keep the highlight inside the visible (zoomed) part of the window
        x0, y0 = max(x0, ox + 4), max(y0, oy + 4)
        x1, y1 = min(x1, ox + shot.width - 4), min(y1, oy + shot.height - 4)
        d.rounded_rectangle([x0, y0, x1, y1], radius=10, outline=GOLD, width=5)
        cx, cy = (x0 + x1) / 2 + 10, (y0 + y1) / 2 + 8           # pointer
        d.polygon([(cx, cy), (cx, cy + 34), (cx + 9, cy + 26), (cx + 16, cy + 41), (cx + 23, cy + 38),
                   (cx + 16, cy + 23), (cx + 27, cy + 22)], fill="white", outline="black")
    return caption_bar(img, caption, step)


def card(title, lines=(), sub=None):
    img = base_canvas()
    d = ImageDraw.Draw(img)
    d.text((W // 2 - d.textlength(title, font=font(64, True)) // 2, 300), title, font=font(64, True), fill=INK)
    if sub:
        d.text((W // 2 - d.textlength(sub, font=font(34)) // 2, 400), sub, font=font(34), fill=MUTED)
    y = 500
    for ln, col in lines:
        d.text((W // 2 - d.textlength(ln, font=font(34)) // 2, y), ln, font=font(34), fill=col)
        y += 60
    return img


def title_card():
    img = base_canvas()
    d = ImageDraw.Draw(img)
    logo = Image.open(os.path.join(ROOT, "packaging", "redactr.png")).convert("RGBA").resize((300, 300))
    img.paste(logo, (W // 2 - 150, 150), logo)
    f = font(96, True)
    tw = d.textlength("Я", font=f) + d.textlength("edactR", font=f)
    x = W // 2 - tw / 2
    d.text((x, 480), "Я", font=f, fill=CORAL)
    d.text((x + d.textlength("Я", font=f), 480), "edactR", font=f, fill=INK)
    t = "Sanitize confidential documents before you share them with AI"
    d.text((W // 2 - d.textlength(t, font=font(40)) // 2, 625), t, font=font(40), fill=MUTED)
    cx = W // 2 - 420
    for label, col in (("100% offline", GOLD), ("5 levels + custom", CORAL), ("Reversible", GOLD), ("OCR built in", CORAL)):
        fw = d.textlength(label, font=font(28, True))
        d.rounded_rectangle([cx, 720, cx + fw + 44, 772], radius=26, fill=col)
        d.text((cx + 22, 727), label, font=font(28, True), fill=MIDNIGHT)
        cx += fw + 64
    return img


def side_by_side(left, right, title, cap, step):
    img = base_canvas()
    d = ImageDraw.Draw(img)
    d.text((W // 2 - d.textlength(title, font=font(44, True)) // 2, 84), title, font=font(44, True), fill=INK)
    pairs = ((left, "Original", CORAL), (right, "Sanitized copy (what you upload)", GOLD))
    if left.width / left.height > 1.6:            # wide documents: stack top/bottom so the text is readable
        box_w, box_h = W - 120, (H - 160 - 140 - 30) // 2
        for i, (im, label, col) in enumerate(pairs):
            y = 150 + i * (box_h + 30)
            d.rounded_rectangle([60, y, 60 + box_w, y + box_h], radius=18, fill=DUSK)
            d.text((84, y + 12), label, font=font(26, True), fill=col)
            s = min((box_w - 300) / im.width, (box_h - 30) / im.height)
            r = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
            img.paste(r, (60 + (box_w - r.width) // 2, y + 15))
        return caption_bar(img, cap, step)
    box_w, box_h = (W - 160) // 2, H - 170 - 160
    for i, (im, label, col) in enumerate(pairs):
        x = 60 + i * (box_w + 40)
        d.rounded_rectangle([x, 160, x + box_w, 160 + box_h + 60], radius=18, fill=DUSK)
        d.text((x + 24, 172), label, font=font(28, True), fill=col)
        s = min((box_w - 40) / im.width, (box_h - 20) / im.height)
        r = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        img.paste(r, (x + (box_w - r.width) // 2, 220))
    return caption_bar(img, cap, step)


def levels_card(sentence):
    img = base_canvas()
    d = ImageDraw.Draw(img)
    t = "One sentence, five levels"
    d.text((W // 2 - d.textlength(t, font=font(48, True)) // 2, 90), t, font=font(48, True), fill=INK)
    y = 190
    d.rounded_rectangle([60, y, W - 60, y + 90], radius=16, fill=DUSK)
    d.text((90, y + 14), "Original", font=font(22, True), fill=CORAL)
    d.text((90, y + 44), sentence, font=mono(26), fill=INK)
    y += 110
    for key in ("L1", "L2", "L3", "L4", "L5"):
        p = LEVELS_BY_KEY[key]
        s = Sanitizer(p, Vault())
        s.scan(sentence, "demo")
        out = s.plan().sub(sentence)
        d.rounded_rectangle([60, y, W - 60, y + 90], radius=16, fill=DUSK)
        d.text((90, y + 14), p.name + "  -  " + p.tagline, font=font(22, True), fill=GOLD)
        d.text((90, y + 44), out, font=mono(26), fill=INK)
        y += 108
    return caption_bar(img, "Pick how much to hide - or build your own Custom level", "Levels")


def render_pdf(path, clip=None, zoom=2.2):
    page = pymupdf.open(path)[0]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


# ------------------------------------------------------------------ the recording
def descendants(w):
    for c in w.winfo_children():
        yield c
        yield from descendants(c)


def main():
    proj_dir = os.path.join(WORK, "Acme Q3 review")
    gui.App._startup = lambda self: None
    app = gui.App()
    app.state("normal")
    # Windows only repaints on-screen windows, so record on-screen but fully transparent and
    # click-through: the user never sees it and their mouse clicks pass straight through it.
    app.geometry("1760x1250+20+20")
    app.attributes("-alpha", 0.0)
    app.update()
    GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT = -20, 0x80000, 0x20
    h = int(app.wm_frame(), 16)
    user32.SetWindowLongW(h, GWL_EXSTYLE, user32.GetWindowLongW(h, GWL_EXSTYLE) | WS_EX_LAYERED | WS_EX_TRANSPARENT)
    app.update()
    app.project = Project.create(proj_dir, "Acme Q3 review", password="demo")
    app._project_loaded()
    app.update()
    hwnd = int(app.wm_frame(), 16)
    vid = Video(OUT)

    def shot():
        app.update()
        return grab(hwnd)

    def where(widget):
        img, (left, top) = shot()
        return (widget.winfo_rootx() - left, widget.winfo_rooty() - top, widget.winfo_width(), widget.winfo_height())

    def film(caption, step, seconds, focus_widget=None, interval=0.1, speed=1.0, view_widget=None, view_rect=None):
        """Record the live window for `seconds` of video (speed > 1 = time-lapse).
        The frame zooms on view_widget (default: the highlighted widget's panel)."""
        f = where(focus_widget) if focus_widget is not None else None
        vw = view_widget if view_widget is not None else focus_widget
        v = view_rect or (where(vw) if vw is not None else None)
        end = time.time() + seconds * speed
        while True:
            t0 = time.time()
            img, _ = shot()
            vid.add(compose_app(img, caption, step, f, v), 1 / FPS)
            if time.time() >= end:
                break
            time.sleep(max(0, interval * speed - (time.time() - t0)))

    # 1 - title
    vid.add(title_card(), 4)
    vid.add(card("Why ЯedactR?", [
        ("Contracts, payroll, client reports... people paste them into AI chatbots every day.", INK),
        ("ЯedactR swaps names, companies, contacts, IDs and numbers for fictional ones first,", INK),
        ("then puts the real values back into the AI's answer.  Nothing ever leaves your PC.", GOLD)]), 6)

    # 2 - project
    film("Create a project - its mapping vault is encrypted with your password", "1", 3, app.proj_label, view_widget=app.proj_label.master)

    # 3 - add files one by one
    files = ["budget_review.docx", "payroll.xlsx", "falcon_deck.pptx", "memo.pdf", "memo_scanned.pdf", "invoice_scan.png"]
    for f in files:
        app._add_paths([os.path.join(SAMPLES, f)])
        film("Add Word, Excel, PowerPoint, PDF, scanned PDF and images", "2", 0.6, app.file_list, view_widget=app.file_list.master.master)
    film("Add Word, Excel, PowerPoint, PDF, scanned PDF and images", "2", 1.2, app.file_list, view_widget=app.file_list.master.master)

    # 4 - levels
    radios = {str(w.cget("value")): w for w in descendants(app.tab_sanitize) if w.winfo_class() == "TRadiobutton"}
    for key in ("L1", "L2", "L5", "L3"):
        app.level.set(key)
        app._level_changed()
        film("Choose a level: from 'names only' up to 'Top Secret'", "3", 1.6, radios.get(key), view_widget=app.level_desc.master)

    # 5 - company names box
    entry = next(w for w in descendants(app.tab_sanitize)
                 if w.winfo_class() == "TEntry" and str(w.cget("textvariable")) == str(app.quick_terms))
    target = "Globex, Initech, Acme Widgets"
    for i in range(1, len(target) + 1, 2):
        app.quick_terms.set(target[:i])
        film("Type your own company & client names - always hidden", "4", 0.12, entry, view_widget=app.file_list.master.master)
    app.quick_terms.set(target)
    film("Type your own company & client names - always hidden", "4", 1.0, entry, view_widget=app.file_list.master.master)

    # 6 - scan (time-lapse while OCR runs)
    film("Scan - everything runs locally, including OCR", "5", 0.8, app.btn_scan)
    app.scan()
    while app._busy:
        film("Scanning... (time-lapse)", "5", 0.5, None, interval=0.1, speed=4)
    film("Review everything that was found and what replaces it", "6", 2.5, app.tree)
    rows = app.tree.get_children()
    for frac in (0.25, 0.5, 0.75, 1.0, 0.0):
        app.tree.yview_moveto(frac)
        film("Review everything that was found and what replaces it", "6", 1.0, app.tree)
    # keep one value
    keep = next((k for k in rows if app.tree.set(k, "original") in ("Chicago",)), rows[min(3, len(rows) - 1)])
    app.tree.see(keep)
    app.tree.selection_set(keep)
    film("Untick anything that should stay as it is", "6", 1.2, app.tree)
    app._toggle(keep)
    film("Untick anything that should stay as it is", "6", 1.6, app.tree)

    # 7 - create copies
    film("Create sanitized copies", "7", 0.8, app.btn_apply)
    app.apply()
    while app._busy:
        film("Writing sanitized copies... (time-lapse)", "7", 0.5, None, interval=0.1, speed=4)
    film("Done: sanitized copies, a leak check for every file, and a full report", "7", 3.0, app.result_frame, view_widget=app.result_frame.master)

    for r in app.job.results.values():
        print(f"  {os.path.basename(r.source)}: {r.status}, {r.replaced} replacements, leaks={r.leaks}")
    san = app.project.sanitized_dir
    # 8 - before / after
    clip = pymupdf.Rect(50, 55, 560, 290)
    vid.add(side_by_side(render_pdf(os.path.join(SAMPLES, "memo.pdf"), clip),
                         render_pdf(os.path.join(san, "memo_sanitized.pdf"), clip),
                         "PDF memo", "Same document, same layout - real identities gone", "8"), 5)
    vid.add(side_by_side(render_pdf(os.path.join(SAMPLES, "memo_scanned.pdf"), clip),
                         render_pdf(os.path.join(san, "memo_scanned_sanitized.pdf"), clip),
                         "Scanned PDF (OCR)", "Even scanned pages: sensitive words are removed from the image", "8"), 5)
    vid.add(side_by_side(Image.open(os.path.join(SAMPLES, "invoice_scan.png")).convert("RGB"),
                         Image.open(os.path.join(san, "invoice_scan_sanitized.png")).convert("RGB"),
                         "Screenshot / photo (OCR)", "Images too - plus a clean text copy for the AI", "8"), 5)

    # 9 - levels comparison
    vid.add(levels_card("Sarah Johnson (sarah@acme.com) of Acme Widgets Inc approved $1.2M on March 3, 2024."), 8)

    # 10 - restore an AI answer
    app.nb.select(app.tab_restore)
    real = ("Summary for Sarah Johnson (CFO, Acme Widgets Inc.):\n"
            "- The revised budget was approved after the call with Globex Corporation.\n"
            "- Next step: Priya Sharma should email priya.sharma@acmewidgets.com before Friday.\n"
            "- Risk: the SSN 219-09-9999 and the VPN password should never be in an email.")
    fake = app.job.sanitizer.plan().sub(real)
    app.ai_text.delete("1.0", "end")
    app.update()
    restore_btn = next(w for w in descendants(app.tab_restore)
                       if w.winfo_class() == "TButton" and "Restore text" in str(w.cget("text")))
    rb, ra, rr = where(restore_btn), where(app.ai_text), where(app.real_text)
    restore_view = (ra[0] - 10, rb[1] - 14, rr[0] + rr[2] - ra[0] + 20, ra[1] + 330 - rb[1])
    film("Paste the AI's answer - it only ever saw fictional values", "9", 1.0, app.ai_text, view_rect=restore_view)
    for i in range(0, len(fake), 9):
        app.ai_text.delete("1.0", "end")
        app.ai_text.insert("1.0", fake[:i + 9])
        film("Paste the AI's answer - it only ever saw fictional values", "9", 0.1, app.ai_text, view_rect=restore_view)
    film("Press Restore", "9", 1.0, restore_btn, view_rect=restore_view)
    app.do_restore_text()
    film("The real names, emails and numbers are back - highlighted", "9", 4.0, app.real_text, view_rect=restore_view)

    # 11 - outro
    vid.add(card("Download ЯedactR - free", [
        ("github.com/ahad26/RedactR", GOLD),
        ("Windows 10 / 11  ·  no install  ·  no admin rights  ·  works offline", INK),
        ("Software by Ahad  ·  github.com/ahad26", MUTED)], sub="Word · Excel · PowerPoint · PDF · images"), 6)

    vid.close()
    app.destroy()
    print(f"wrote {OUT}: {vid.frames} frames = {vid.frames / FPS:.1f}s")


if __name__ == "__main__":
    try:
        main()
    finally:
        shutil.rmtree(WORK, ignore_errors=True)
