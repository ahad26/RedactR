"""ЯedactR desktop application (Tkinter - runs 100% locally, no browser, no server)."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, simpledialog, ttk

from . import APP_NAME, __version__, config, formats, ocr, splash
from .categories import CATEGORIES, CATEGORY_ORDER
from .levels import LEVELS, REALISTIC, TOKEN, Profile
from .pipeline import SanitizeJob, restore_file, restore_text
from .project import Project
from .vault import VaultError, norm

# Palette: #312C51 (midnight), #48426D (dusk), #F0C38E (gold), #F1AA9B (coral)
MIDNIGHT = "#312C51"
DUSK = "#48426D"
GOLD = "#F0C38E"
CORAL = "#F1AA9B"
BG = MIDNIGHT            # window background
PANEL = DUSK             # cards
FIELD = MIDNIGHT         # inputs, tables, text boxes inside cards
INK = "#F7F4FB"          # main text
MUTED = "#C9C3E3"        # secondary text
LINE = "#5E5788"         # borders, hover
ACCENT = GOLD            # primary actions
ACCENT_DARK = "#E2AD70"
HEADER = MIDNIGHT
OK = GOLD
BAD = CORAL
CHECK, UNCHECK = "☑", "☐"


def open_path(p: str):
    if not p:
        return
    if sys.platform.startswith("win"):
        os.startfile(p)  # noqa: S606 - opens local folder/file with the default app
    elif sys.platform == "darwin":
        subprocess.Popen(["open", p])
    else:
        subprocess.Popen(["xdg-open", p])


# =========================================================================== dialogs
class NewProjectDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("New project")
        self.configure(bg=PANEL, padx=20, pady=16)
        self.resizable(False, False)
        self.result = None
        self.transient(master)
        self.parent_dir = tk.StringVar(value=config.default_projects_dir())
        self.name = tk.StringVar(value="My Project")
        self.pw1, self.pw2 = tk.StringVar(), tk.StringVar()
        r = 0
        ttk.Label(self, text="Create a project", style="H2.TLabel").grid(row=r, column=0, columnspan=3, sticky="w"); r += 1
        ttk.Label(self, text="A project keeps the mapping vault, sanitized copies, reports and restored files together.\n"
                             "Use one project per piece of work so names stay consistent and answers can be restored.",
                  style="Muted.TLabel", wraplength=460, justify="left").grid(row=r, column=0, columnspan=3, sticky="w", pady=(2, 10)); r += 1
        ttk.Label(self, text="Project name").grid(row=r, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.name, width=40).grid(row=r, column=1, columnspan=2, sticky="we", pady=3); r += 1
        ttk.Label(self, text="Save in").grid(row=r, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.parent_dir, width=40).grid(row=r, column=1, sticky="we", pady=3)
        ttk.Button(self, text="Browse...", command=self._browse).grid(row=r, column=2, padx=(6, 0)); r += 1
        ttk.Label(self, text="Vault password").grid(row=r, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.pw1, show="•").grid(row=r, column=1, columnspan=2, sticky="we", pady=3); r += 1
        ttk.Label(self, text="Repeat password").grid(row=r, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.pw2, show="•").grid(row=r, column=1, columnspan=2, sticky="we", pady=3); r += 1
        ttk.Label(self, text="Recommended. The vault links fictional values back to the real ones, so protect it.\n"
                             "Leave empty for no password. A forgotten password cannot be recovered.",
                  style="Muted.TLabel", justify="left").grid(row=r, column=0, columnspan=3, sticky="w", pady=(2, 10)); r += 1
        bf = ttk.Frame(self, style="Panel.TFrame")
        bf.grid(row=r, column=0, columnspan=3, sticky="e")
        ttk.Button(bf, text="Cancel", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(bf, text="Create project", style="Accent.TButton", command=self._ok).pack(side="right")
        self.grab_set()
        self.wait_window()

    def _browse(self):
        d = filedialog.askdirectory(parent=self, initialdir=self.parent_dir.get())
        if d:
            self.parent_dir.set(d)

    def _ok(self):
        name = self.name.get().strip()
        if not name:
            messagebox.showerror(APP_NAME, "Please enter a project name.", parent=self)
            return
        if self.pw1.get() != self.pw2.get():
            messagebox.showerror(APP_NAME, "The passwords do not match.", parent=self)
            return
        folder = os.path.join(self.parent_dir.get(), "".join(c for c in name if c not in '<>:"/\\|?*').strip())
        if Project.is_project(folder):
            messagebox.showerror(APP_NAME, "A project already exists in that folder - use Open project.", parent=self)
            return
        self.result = (folder, name, self.pw1.get() or None)
        self.destroy()


class AddTermDialog(tk.Toplevel):
    def __init__(self, master, initial=""):
        super().__init__(master)
        self.title("Add a value to hide")
        self.configure(bg=PANEL, padx=18, pady=14)
        self.transient(master)
        self.result = None
        self.value = tk.StringVar(value=initial)
        self.cat = tk.StringVar(value="CUSTOM")
        ttk.Label(self, text="Text to hide (exact word or phrase)").grid(row=0, column=0, sticky="w")
        e = ttk.Entry(self, textvariable=self.value, width=44)
        e.grid(row=1, column=0, columnspan=2, sticky="we", pady=(2, 8))
        ttk.Label(self, text="Category").grid(row=2, column=0, sticky="w")
        ttk.Combobox(self, textvariable=self.cat, values=CATEGORY_ORDER, state="readonly", width=18).grid(row=2, column=1, sticky="w")
        self.remember = tk.BooleanVar(value=True)
        ttk.Checkbutton(self, text="Always hide this in this project (adds to the custom term list)",
                        variable=self.remember).grid(row=3, column=0, columnspan=2, sticky="w", pady=8)
        bf = ttk.Frame(self, style="Panel.TFrame")
        bf.grid(row=4, column=0, columnspan=2, sticky="e")
        ttk.Button(bf, text="Cancel", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(bf, text="Add", style="Accent.TButton", command=self._ok).pack(side="right")
        e.focus_set()
        self.bind("<Return>", lambda _e: self._ok())
        self.grab_set()
        self.wait_window()

    def _ok(self):
        v = self.value.get().strip()
        if v:
            self.result = (v, self.cat.get(), self.remember.get())
        self.destroy()


# =========================================================================== main app
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = config.load()
        if self.cfg.get("tesseract_path"):
            ocr.set_tesseract_path(self.cfg["tesseract_path"])
        self.title(f"{APP_NAME} - sanitize documents before sharing with AI")
        # size relative to display scaling so everything fits at 100%-200% Windows scaling
        f = max(1.0, self.winfo_fpixels("1i") / 96)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(int(1300 * f), sw - 40), min(int(900 * f), sh - 90)
        self.geometry(f"{w}x{h}+{max(0, (sw - w) // 2)}+{max(0, (sh - h) // 3)}")
        self.minsize(min(int(1000 * f), sw - 40), min(int(660 * f), sh - 90))
        if w >= sw - 40 or h >= sh - 90:
            try:
                self.state("zoomed")
            except tk.TclError:
                pass
        self.configure(bg=BG)
        try:
            self.iconbitmap(default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "redactr.ico"))
        except tk.TclError:
            pass
        self.project: Project | None = None
        self.job: SanitizeJob | None = None
        self.files: list[str] = []
        self.level = tk.StringVar(value="L3")
        self.use_ocr = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Ready")
        self.q: queue.Queue = queue.Queue()
        self._busy = False
        self._style()
        self._build()
        self.after(100, self._poll)
        self.after(200, self._startup)
        self.protocol("WM_DELETE_WINDOW", self._close)

    # ------------------------------------------------------------------ style
    def _style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        base = ("Segoe UI", 10)
        bold = ("Segoe UI", 10, "bold")
        self.option_add("*Font", base)
        # classic Tk widgets (text boxes, lists, combobox drop-downs)
        for w in ("Text", "Listbox"):
            self.option_add(f"*{w}.background", FIELD)
            self.option_add(f"*{w}.foreground", INK)
            self.option_add(f"*{w}.selectBackground", GOLD)
            self.option_add(f"*{w}.selectForeground", MIDNIGHT)
            self.option_add(f"*{w}.highlightThickness", 1)
            self.option_add(f"*{w}.highlightBackground", LINE)
            self.option_add(f"*{w}.highlightColor", GOLD)
        self.option_add("*Text.insertBackground", GOLD)
        self.option_add("*TCombobox*Listbox.background", FIELD)
        self.option_add("*TCombobox*Listbox.foreground", INK)
        self.option_add("*TCombobox*Listbox.selectBackground", GOLD)
        self.option_add("*TCombobox*Listbox.selectForeground", MIDNIGHT)

        s.configure(".", background=BG, foreground=INK, font=base, bordercolor=LINE, lightcolor=PANEL,
                    darkcolor=PANEL, troughcolor=MIDNIGHT, focuscolor=GOLD, insertcolor=INK,
                    selectbackground=GOLD, selectforeground=MIDNIGHT, fieldbackground=FIELD)
        s.configure("TFrame", background=BG)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("Header.TFrame", background=HEADER)
        s.configure("TLabel", background=BG, foreground=INK)
        s.configure("Panel.TLabel", background=PANEL, foreground=INK)
        s.configure("H1.TLabel", font=("Segoe UI", 20, "bold"), background=HEADER, foreground=INK)
        s.configure("HeaderMuted.TLabel", background=HEADER, foreground=MUTED)
        s.configure("H2.TLabel", font=("Segoe UI", 13, "bold"), background=PANEL, foreground=INK)
        s.configure("H3.TLabel", font=("Segoe UI", 11, "bold"), background=PANEL, foreground=INK)
        s.configure("Muted.TLabel", foreground=MUTED, background=PANEL)
        s.configure("BgMuted.TLabel", foreground=MUTED, background=BG)
        s.configure("Ok.TLabel", foreground=OK, background=PANEL, font=bold)
        s.configure("Bad.TLabel", foreground=BAD, background=PANEL, font=bold)

        for w in ("TCheckbutton", "TRadiobutton", "Level.TRadiobutton"):
            s.configure(w, background=PANEL, foreground=INK, indicatorbackground=FIELD,
                        indicatorforeground=GOLD, indicatormargin=(0, 0, 6, 0), upperbordercolor=LINE,
                        lowerbordercolor=LINE)
            s.map(w, background=[("active", PANEL)], foreground=[("disabled", MUTED)],
                  indicatorbackground=[("selected", FIELD), ("active", LINE)])
        s.configure("Level.TRadiobutton", font=bold)

        # buttons: gold primary, midnight secondary
        s.configure("TButton", padding=(10, 5), background=MIDNIGHT, foreground=INK, bordercolor=LINE,
                    lightcolor=MIDNIGHT, darkcolor=MIDNIGHT, focusthickness=0)
        s.map("TButton", background=[("disabled", PANEL), ("pressed", LINE), ("active", "#3D3766")],
              foreground=[("disabled", MUTED)], bordercolor=[("active", GOLD)])
        s.configure("Accent.TButton", background=GOLD, foreground=MIDNIGHT, bordercolor=GOLD, lightcolor=GOLD,
                    darkcolor=GOLD, padding=(14, 6), font=bold)
        s.map("Accent.TButton",
              background=[("disabled", "#7D7397"), ("pressed", ACCENT_DARK), ("active", ACCENT_DARK)],
              foreground=[("disabled", "#B9B2D3")],
              bordercolor=[("active", ACCENT_DARK), ("disabled", "#7D7397")])
        s.configure("Header.TButton", background=DUSK, foreground=INK, bordercolor=DUSK, lightcolor=DUSK,
                    darkcolor=DUSK)
        s.map("Header.TButton", background=[("active", LINE)], bordercolor=[("active", GOLD)])

        # inputs
        s.configure("TEntry", fieldbackground=FIELD, foreground=INK, bordercolor=LINE, insertcolor=GOLD,
                    lightcolor=FIELD, darkcolor=FIELD)
        s.map("TEntry", bordercolor=[("focus", GOLD)], lightcolor=[("focus", GOLD)])
        s.configure("TCombobox", fieldbackground=FIELD, background=DUSK, foreground=INK, arrowcolor=GOLD,
                    bordercolor=LINE, lightcolor=FIELD, darkcolor=FIELD)
        s.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", INK)],
              selectbackground=[("readonly", FIELD)], selectforeground=[("readonly", INK)],
              background=[("active", LINE)])
        s.configure("Vertical.TScrollbar", background=DUSK, troughcolor=MIDNIGHT, arrowcolor=GOLD,
                    bordercolor=MIDNIGHT, lightcolor=DUSK, darkcolor=DUSK)
        s.map("Vertical.TScrollbar", background=[("active", LINE)])

        # tabs
        s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        s.configure("TNotebook.Tab", padding=(18, 8), font=bold, background="#3B3562", foreground=MUTED,
                    bordercolor=MIDNIGHT, lightcolor="#3B3562")
        s.map("TNotebook.Tab", background=[("selected", PANEL), ("active", "#423C69")],
              foreground=[("selected", GOLD), ("active", INK)], lightcolor=[("selected", PANEL)])

        # tables
        s.configure("Treeview", rowheight=28, background=FIELD, fieldbackground=FIELD, foreground=INK,
                    bordercolor=LINE, lightcolor=FIELD, darkcolor=FIELD)
        s.map("Treeview", background=[("selected", GOLD)], foreground=[("selected", MIDNIGHT)])
        s.configure("Treeview.Heading", font=bold, background=GOLD, foreground=MIDNIGHT,
                    bordercolor=ACCENT_DARK, lightcolor=GOLD, darkcolor=ACCENT_DARK, relief="flat")
        s.map("Treeview.Heading", background=[("active", ACCENT_DARK)])

        s.configure("TLabelframe", background=PANEL)
        s.configure("TLabelframe.Label", background=PANEL, foreground=INK, font=bold)
        s.configure("TSeparator", background=LINE)
        s.configure("red.Horizontal.TProgressbar", background=GOLD, troughcolor=DUSK, bordercolor=MIDNIGHT,
                    lightcolor=GOLD, darkcolor=ACCENT_DARK)

    def _panel(self, parent, **kw):
        f = ttk.Frame(parent, style="Panel.TFrame", padding=14, **kw)
        return f

    # ------------------------------------------------------------------ layout
    def _build(self):
        hdr = ttk.Frame(self, style="Header.TFrame", padding=(18, 10))
        hdr.pack(fill="x")
        logo = tk.Frame(hdr, bg=HEADER)
        logo.pack(side="left")
        tk.Label(logo, text="Я", fg=CORAL, bg=HEADER, font=("Segoe UI Black", 22)).pack(side="left")
        tk.Label(logo, text="edactR", fg=INK, bg=HEADER, font=("Segoe UI", 20, "bold")).pack(side="left")
        ttk.Label(hdr, text="   Sanitize confidential documents locally before using AI", style="HeaderMuted.TLabel").pack(side="left")
        ttk.Button(hdr, text="Open project", style="Header.TButton", command=self.open_project).pack(side="right", padx=(6, 0))
        ttk.Button(hdr, text="New project", style="Header.TButton", command=self.new_project).pack(side="right")
        self.proj_label = ttk.Label(hdr, text="No project open", style="HeaderMuted.TLabel")
        self.proj_label.pack(side="right", padx=12)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        self.tab_sanitize = ttk.Frame(self.nb, padding=4)
        self.tab_restore = ttk.Frame(self.nb, padding=4)
        self.tab_custom = ttk.Frame(self.nb, padding=4)
        self.tab_vault = ttk.Frame(self.nb, padding=4)
        self.tab_settings = ttk.Frame(self.nb, padding=4)
        self.nb.add(self.tab_sanitize, text="  1  Sanitize  ")
        self.nb.add(self.tab_restore, text="  2  Restore AI response  ")
        self.nb.add(self.tab_custom, text="  Custom level & terms  ")
        self.nb.add(self.tab_vault, text="  Mapping vault  ")
        self.nb.add(self.tab_settings, text="  Settings & help  ")
        self.nb.bind("<<NotebookTabChanged>>", lambda _e: self._tab_changed())

        self._build_sanitize()
        self._build_restore()
        self._build_custom()
        self._build_vault()
        self._build_settings()

        sb = ttk.Frame(self, padding=(14, 6))
        sb.pack(fill="x")
        self.progress = ttk.Progressbar(sb, length=220, mode="determinate", style="red.Horizontal.TProgressbar")
        self.progress.pack(side="right")
        ttk.Label(sb, textvariable=self.status, style="BgMuted.TLabel").pack(side="left")
        ttk.Label(sb, text="Offline - nothing leaves this computer   ", style="BgMuted.TLabel").pack(side="right")

    # ------------------------------------------------------------------ sanitize tab
    def _build_sanitize(self):
        t = self.tab_sanitize
        t.columnconfigure(0, weight=0, minsize=420)
        t.columnconfigure(1, weight=1)
        t.rowconfigure(0, weight=1)

        left = ttk.Frame(t)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.rowconfigure(1, weight=1)

        # files
        fp = self._panel(left)
        fp.grid(row=0, column=0, sticky="nsew")
        ttk.Label(fp, text="Step 1 - Choose files", style="H2.TLabel").pack(anchor="w")
        ttk.Label(fp, text="Word, PDF, Excel, PowerPoint, CSV, text and images (OCR)", style="Muted.TLabel").pack(anchor="w")
        lf = ttk.Frame(fp, style="Panel.TFrame")
        lf.pack(fill="both", expand=True, pady=6)
        self.file_list = tk.Listbox(lf, height=5, activestyle="none", borderwidth=0, relief="flat",
                                    selectmode="extended")
        self.file_list.pack(side="left", fill="both", expand=True)
        sc = ttk.Scrollbar(lf, command=self.file_list.yview)
        sc.pack(side="right", fill="y")
        self.file_list.configure(yscrollcommand=sc.set)
        bf = ttk.Frame(fp, style="Panel.TFrame")
        bf.pack(fill="x")
        ttk.Button(bf, text="Add files...", command=self.add_files).pack(side="left")
        ttk.Button(bf, text="Add folder...", command=self.add_folder).pack(side="left", padx=4)
        ttk.Button(bf, text="Remove", command=self.remove_files).pack(side="left")
        ttk.Button(bf, text="Clear", command=self.clear_files).pack(side="left", padx=4)
        ttk.Label(fp, text="Company & client names to always hide (every level)", style="H3.TLabel").pack(anchor="w", pady=(10, 2))
        self.quick_terms = tk.StringVar()
        ttk.Entry(fp, textvariable=self.quick_terms).pack(fill="x")
        ttk.Label(fp, text="Comma separated, e.g.  Globex, Initech, Acme Widgets.  Saved with the project.",
                  style="Muted.TLabel").pack(anchor="w")

        # level
        lp = self._panel(left)
        lp.grid(row=1, column=0, sticky="nsew", pady=10)
        ttk.Label(lp, text="Step 2 - Choose sanitization level", style="H2.TLabel").pack(anchor="w", pady=(0, 6))
        for p in LEVELS + [Profile("CUSTOM", "Custom", "Your own categories, terms & patterns", "", [])]:
            row = ttk.Frame(lp, style="Panel.TFrame")
            row.pack(fill="x", pady=1)
            ttk.Radiobutton(row, text=p.name, value=p.key, variable=self.level, style="Level.TRadiobutton",
                            command=self._level_changed).pack(side="left")
            ttk.Label(row, text=" - " + p.tagline, style="Muted.TLabel").pack(side="left")
        self.level_desc = ttk.Label(lp, text="", style="Muted.TLabel", wraplength=390, justify="left")
        self.level_desc.pack(anchor="w", pady=(8, 0), fill="x")
        self.level_cats = ttk.Label(lp, text="", style="Muted.TLabel", wraplength=390, justify="left")
        self.level_cats.pack(anchor="w", pady=(4, 0), fill="x")

        # actions
        ap = self._panel(left)
        ap.grid(row=2, column=0, sticky="ew")
        ttk.Label(ap, text="Step 3 - Scan, review, create", style="H2.TLabel").pack(anchor="w")
        self.ocr_check = ttk.Checkbutton(ap, text="Use OCR for images and scanned PDFs", variable=self.use_ocr)
        self.ocr_check.pack(anchor="w", pady=4)
        bf2 = ttk.Frame(ap, style="Panel.TFrame")
        bf2.pack(fill="x", pady=(4, 0))
        self.btn_scan = ttk.Button(bf2, text="Scan for sensitive data", command=self.scan)
        self.btn_scan.pack(side="left")
        self.btn_apply = ttk.Button(bf2, text="Create sanitized copies", style="Accent.TButton", command=self.apply,
                                    state="disabled")
        self.btn_apply.pack(side="left", padx=8)

        # review panel
        rp = self._panel(t)
        rp.grid(row=0, column=1, sticky="nsew")
        rp.rowconfigure(2, weight=1)
        rp.columnconfigure(0, weight=1)
        top = ttk.Frame(rp, style="Panel.TFrame")
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="Review what will be hidden", style="H2.TLabel").pack(side="left")
        self.review_count = ttk.Label(top, text="", style="Muted.TLabel")
        self.review_count.pack(side="right")
        ttk.Label(rp, text="Click the box to keep a value unchanged. Double-click a replacement to edit it. "
                           "Something missed? Use 'Add value'.", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 6))
        tf = ttk.Frame(rp, style="Panel.TFrame")
        tf.grid(row=2, column=0, sticky="nsew")
        cols = ("inc", "original", "category", "replacement", "count", "files")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="extended")
        for c, w, txt in [("inc", 50, "Hide"), ("original", 230, "Original value"), ("category", 120, "Category"),
                          ("replacement", 220, "Will be replaced with"), ("count", 60, "Found"), ("files", 180, "Files")]:
            self.tree.heading(c, text=txt, command=lambda c=c: self._sort_tree(c))
            self.tree.column(c, width=w, anchor="center" if c in ("inc", "count") else "w", stretch=c not in ("inc", "count"))
        self.tree.pack(side="left", fill="both", expand=True)
        vs = ttk.Scrollbar(tf, command=self.tree.yview)
        vs.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.tag_configure("off", foreground="#8E87B5")
        self.tree.bind("<Button-1>", self._tree_click)
        self.tree.bind("<Double-1>", self._tree_double)
        self.tree.bind("<space>", lambda _e: self._toggle_selected())
        bar = ttk.Frame(rp, style="Panel.TFrame")
        bar.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(bar, text="Add value...", command=self.add_value).pack(side="left")
        ttk.Button(bar, text="Hide selected", command=lambda: self._set_selected(True)).pack(side="left", padx=4)
        ttk.Button(bar, text="Keep selected", command=lambda: self._set_selected(False)).pack(side="left")
        ttk.Button(bar, text="Never hide selected", command=self.never_hide).pack(side="left", padx=4)
        self.filter_var = tk.StringVar()
        fe = ttk.Entry(bar, textvariable=self.filter_var, width=22)
        fe.pack(side="right")
        ttk.Label(bar, text="Filter ", style="Muted.TLabel").pack(side="right")
        self.filter_var.trace_add("write", lambda *_: self._refresh_tree())

        self.result_frame = ttk.Frame(rp, style="Panel.TFrame")
        self.result_frame.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self._level_changed()

    # ------------------------------------------------------------------ restore tab
    def _build_restore(self):
        t = self.tab_restore
        t.columnconfigure(0, weight=1)
        t.columnconfigure(1, weight=1)
        t.rowconfigure(1, weight=1)
        intro = self._panel(t)
        intro.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Label(intro, text="Bring the AI's answer back to reality", style="H2.TLabel").pack(anchor="w")
        ttk.Label(intro, text="Paste the AI's response (which mentions the fictional names / placeholders) on the left and press "
                              "Restore. Every fictional value from this project's vault is swapped back to the real one. "
                              "You can also restore a whole file the AI produced (Word, Excel, PowerPoint, PDF, text).",
                  style="Muted.TLabel", wraplength=1150, justify="left").pack(anchor="w")
        bar = ttk.Frame(intro, style="Panel.TFrame")
        bar.pack(fill="x", pady=(8, 0))
        ttk.Button(bar, text="Restore text  →", style="Accent.TButton", command=self.do_restore_text).pack(side="left")
        ttk.Button(bar, text="Restore a file...", command=self.do_restore_file).pack(side="left", padx=6)
        ttk.Button(bar, text="Open restored folder", command=lambda: self.project and open_path(self.project.restored_dir)).pack(side="left")
        self.restore_info = ttk.Label(bar, text="", style="Ok.TLabel")
        self.restore_info.pack(side="left", padx=12)

        lp = self._panel(t)
        lp.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        ttk.Label(lp, text="AI response (with fictional values)", style="H3.TLabel").pack(anchor="w")
        self.ai_text = tk.Text(lp, wrap="word", relief="flat", borderwidth=0, padx=8, pady=6, font=("Segoe UI", 10), undo=True)
        self.ai_text.pack(fill="both", expand=True, pady=(4, 6))
        lb = ttk.Frame(lp, style="Panel.TFrame")
        lb.pack(fill="x")
        ttk.Button(lb, text="Paste", command=self._paste_ai).pack(side="left")
        ttk.Button(lb, text="Clear", command=lambda: self.ai_text.delete("1.0", "end")).pack(side="left", padx=4)

        rp = self._panel(t)
        rp.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        ttk.Label(rp, text="Restored (real values)", style="H3.TLabel").pack(anchor="w")
        self.real_text = tk.Text(rp, wrap="word", relief="flat", borderwidth=0, padx=8, pady=6, font=("Segoe UI", 10))
        self.real_text.pack(fill="both", expand=True, pady=(4, 6))
        self.real_text.tag_configure("hit", background=GOLD, foreground=MIDNIGHT)
        rb = ttk.Frame(rp, style="Panel.TFrame")
        rb.pack(fill="x")
        ttk.Button(rb, text="Copy", command=self._copy_real).pack(side="left")
        ttk.Button(rb, text="Save as...", command=self._save_real).pack(side="left", padx=4)

    # ------------------------------------------------------------------ custom tab
    def _build_custom(self):
        t = self.tab_custom
        t.columnconfigure(0, weight=1)
        t.columnconfigure(1, weight=1)
        t.rowconfigure(0, weight=1)
        cp = self._panel(t)
        cp.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ttk.Label(cp, text="Custom level", style="H2.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(cp, text="Pick what to hide and how. 'Realistic' swaps in believable fictional values (best for AI "
                           "reasoning); 'Placeholder' uses tags like [ORG_2] (safest, always reversible).",
                  style="Muted.TLabel", wraplength=560, justify="left").grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))
        start = ttk.Frame(cp, style="Panel.TFrame")
        start.grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 6))
        ttk.Label(start, text="Start from:", style="Panel.TLabel").pack(side="left")
        for p in LEVELS:
            ttk.Button(start, text=p.key, width=4, command=lambda p=p: self._custom_from(p)).pack(side="left", padx=2)
        self.cat_vars: dict[str, tk.BooleanVar] = {}
        self.style_vars: dict[str, tk.StringVar] = {}
        r = 3
        for key in CATEGORY_ORDER:
            cat = CATEGORIES[key]
            v = tk.BooleanVar()
            s = tk.StringVar(value="Realistic" if cat.can_be_realistic else "Placeholder")
            self.cat_vars[key], self.style_vars[key] = v, s
            ttk.Checkbutton(cp, text=cat.label, variable=v).grid(row=r, column=0, sticky="w")
            ttk.Label(cp, text=cat.description, style="Muted.TLabel").grid(row=r, column=1, sticky="w", padx=6)
            cb = ttk.Combobox(cp, textvariable=s, width=11, state="readonly",
                              values=["Realistic", "Placeholder"] if cat.can_be_realistic else ["Placeholder"])
            cb.grid(row=r, column=2, sticky="e", pady=1)
            r += 1
        self.strip_meta = tk.BooleanVar(value=True)
        ttk.Checkbutton(cp, text="Wipe document metadata (author, company, comments authors)",
                        variable=self.strip_meta).grid(row=r, column=0, columnspan=3, sticky="w", pady=(8, 0))
        cp.columnconfigure(1, weight=1)

        tp = self._panel(t)
        tp.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        ttk.Label(tp, text="Your terms (apply to every level)", style="H2.TLabel").pack(anchor="w")
        ttk.Label(tp, text="Always hide - one per line. Optionally give a category: 'Acme Corp => ORG', "
                           "'Project Falcon' (defaults to custom placeholder).", style="Muted.TLabel",
                  wraplength=520, justify="left").pack(anchor="w")
        self.terms_text = tk.Text(tp, height=8, relief="flat", borderwidth=0, padx=8, pady=6)
        self.terms_text.pack(fill="both", expand=True, pady=(4, 8))
        ttk.Label(tp, text="Never hide - one per line (e.g. your public brand, generic words).", style="Muted.TLabel").pack(anchor="w")
        self.allow_text = tk.Text(tp, height=5, relief="flat", borderwidth=0, padx=8, pady=6)
        self.allow_text.pack(fill="both", expand=True, pady=(4, 8))
        ttk.Label(tp, text="Custom patterns (regular expressions) - 'Label = regex', e.g. 'Matter no = MAT-\\d{6}'",
                  style="Muted.TLabel", wraplength=520).pack(anchor="w")
        self.pattern_text = tk.Text(tp, height=5, relief="flat", borderwidth=0, padx=8, pady=6, font=("Consolas", 10))
        self.pattern_text.pack(fill="both", expand=True, pady=(4, 8))
        ttk.Button(tp, text="Save custom settings", style="Accent.TButton", command=self.save_custom).pack(anchor="e")

    # ------------------------------------------------------------------ vault tab
    def _build_vault(self):
        t = self.tab_vault
        p = self._panel(t)
        p.pack(fill="both", expand=True)
        top = ttk.Frame(p, style="Panel.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="Mapping vault", style="H2.TLabel").pack(side="left")
        self.vault_info = ttk.Label(top, text="", style="Muted.TLabel")
        self.vault_info.pack(side="left", padx=10)
        ttk.Button(top, text="Change password...", command=self.change_password).pack(side="right")
        ttk.Button(top, text="Delete selected", command=self.vault_delete).pack(side="right", padx=4)
        self.vault_filter = tk.StringVar()
        ttk.Entry(top, textvariable=self.vault_filter, width=24).pack(side="right", padx=8)
        ttk.Label(top, text="Search", style="Muted.TLabel").pack(side="right")
        self.vault_filter.trace_add("write", lambda *_: self._refresh_vault())
        ttk.Label(p, text="Every real value and the fictional value that replaced it. This is what makes restoring possible - "
                          "keep the project folder safe and never upload the vault or reports.",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 8))
        tf = ttk.Frame(p, style="Panel.TFrame")
        tf.pack(fill="both", expand=True)
        cols = ("original", "category", "replacement", "created")
        self.vtree = ttk.Treeview(tf, columns=cols, show="headings")
        for c, w, txt in [("original", 320, "Real value"), ("category", 120, "Category"),
                          ("replacement", 320, "Fictional value"), ("created", 160, "Added")]:
            self.vtree.heading(c, text=txt)
            self.vtree.column(c, width=w)
        self.vtree.pack(side="left", fill="both", expand=True)
        vs = ttk.Scrollbar(tf, command=self.vtree.yview)
        vs.pack(side="right", fill="y")
        self.vtree.configure(yscrollcommand=vs.set)

    # ------------------------------------------------------------------ settings tab
    def _build_settings(self):
        t = self.tab_settings
        p = self._panel(t)
        p.pack(fill="both", expand=True)
        ttk.Label(p, text="OCR (images and scanned PDFs)", style="H2.TLabel").pack(anchor="w")
        self.ocr_status = ttk.Label(p, text="", style="Muted.TLabel")
        self.ocr_status.pack(anchor="w", pady=(2, 4))
        ttk.Label(p, text="ЯedactR uses the free, open-source Tesseract OCR engine, running locally - images are never uploaded.\n"
                          "The portable RedactR.exe already contains it (English). When running from source, install it with\n"
                          "    winget install UB-Mannheim.TesseractOCR\nthen restart ЯedactR or point to tesseract.exe below.",
                  style="Muted.TLabel", justify="left").pack(anchor="w")
        bf = ttk.Frame(p, style="Panel.TFrame")
        bf.pack(anchor="w", pady=6)
        ttk.Button(bf, text="Locate tesseract.exe...", command=self.locate_tesseract).pack(side="left")
        ttk.Button(bf, text="Re-check", command=self._update_ocr_status).pack(side="left", padx=4)

        ttk.Separator(p).pack(fill="x", pady=14)
        ttk.Label(p, text="How to use ЯedactR safely", style="H2.TLabel").pack(anchor="w")
        help_text = (
            "1.  Create a project (one per client / case / piece of work) and protect the vault with a password.\n"
            "2.  Add files, pick a level, press Scan. Review the table: untick anything that should stay, add anything missed.\n"
            "3.  Press Create sanitized copies. Upload ONLY the files in the project's 'sanitized' folder to the AI tool.\n"
            "4.  Open the HTML report to see exactly what was removed and what replaced it. Each file also gets a leak check.\n"
            "5.  When the AI answers, paste the answer into 'Restore AI response' - fictional names become real again.\n\n"
            "Levels\n"
            "   Level 1 - Alias: people's names only.\n"
            "   Level 2 - Private: + emails, phones, addresses, IDs, payment cards, dates of birth, passwords & keys.\n"
            "   Level 3 - Confidential: + companies, locations, web/IP addresses, bank accounts, internal IDs, your terms, metadata.\n"
            "   Level 4 - Restricted: + money, dates, percentages and file paths become placeholders.\n"
            "   Level 5 - Top Secret: + every number and proper noun; all replacements are placeholders.\n"
            "   Custom - choose your own categories, replacement style, terms and patterns.\n\n"
            "Tips\n"
            "   - Detection is automatic but not perfect: always review before uploading, and add your client names and\n"
            "     project code names to 'Your terms' so they are always caught.\n"
            "   - Text inside pictures embedded in Word/PowerPoint is not changed (the report warns you when they exist).\n"
            "   - If the AI changes a fictional name (e.g. only uses a nickname) it may not be restored - check the result.\n"
            "   - Realistic replacements of money/dates are never used: those become placeholders so totals stay restorable.")
        ttk.Label(p, text=help_text, style="Panel.TLabel", justify="left").pack(anchor="w", pady=(4, 0))
        ttk.Label(p, text=f"{APP_NAME} {__version__} - runs entirely on this computer.", style="Muted.TLabel").pack(anchor="w", pady=(14, 0))
        self._update_ocr_status()

    # ================================================================== project
    def _startup(self):
        # main window is up: hide the start-up splash and bring the app to the front
        splash.close()
        self.lift()
        self.focus_force()
        last = self.cfg.get("last_project")
        if last and Project.is_project(last):
            self._open_folder(last)
        else:
            if messagebox.askyesno(APP_NAME, "Welcome to ЯedactR!\n\nCreate your first project now?\n"
                                             "(Choose 'No' to open an existing project.)"):
                self.new_project()
            else:
                self.open_project()

    def new_project(self):
        if self._busy:
            return
        d = NewProjectDialog(self)
        if not d.result:
            return
        folder, name, pw = d.result
        try:
            self.project = Project.create(folder, name, pw)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not create the project:\n{exc}")
            return
        self._project_loaded()

    def open_project(self):
        if self._busy:
            return
        d = filedialog.askdirectory(title="Open a ЯedactR project folder",
                                    initialdir=self.cfg.get("last_project") or config.default_projects_dir())
        if d:
            if not Project.is_project(d):
                messagebox.showerror(APP_NAME, "That folder is not a ЯedactR project.")
                return
            self._open_folder(d)

    def _open_folder(self, folder):
        pw = None
        if Project.needs_password(folder):
            for _ in range(3):
                pw = simpledialog.askstring(APP_NAME, f"Vault password for '{os.path.basename(folder)}':", show="•", parent=self)
                if pw is None:
                    return
                try:
                    self.project = Project.open(folder, pw)
                    break
                except VaultError as exc:
                    messagebox.showerror(APP_NAME, str(exc))
            else:
                return
        else:
            try:
                self.project = Project.open(folder)
            except Exception as exc:
                messagebox.showerror(APP_NAME, f"Could not open the project:\n{exc}")
                return
        self._project_loaded()

    def _project_loaded(self):
        p = self.project
        self.cfg["last_project"] = p.folder
        config.save(self.cfg)
        lock = "\U0001F512 " if p.password else ""
        self.proj_label.configure(text=f"{lock}Project: {p.name}")
        self.level.set(p.settings.get("level", "L3"))
        self._load_custom_into_form()
        self._level_changed()
        self._reset_review()
        self._refresh_vault()
        self.status.set(f"Project opened: {p.folder}")

    # "Company & client names" box <-> project custom terms tagged '=> ORG'
    @staticmethod
    def _is_org_term(t: str) -> bool:
        return "=>" in t and t.split("=>", 1)[1].strip().upper() == "ORG"

    def _save_quick_terms(self):
        names = []
        for n in self.quick_terms.get().replace(";", ",").replace("\n", ",").split(","):
            n = n.strip()
            if n and n.lower() not in (x.lower() for x in names):
                names.append(n)
        cp = self.project.custom_profile()
        new_terms = [t for t in cp.custom_terms if not self._is_org_term(t)] + [f"{n} => ORG" for n in names]
        if new_terms != cp.custom_terms:
            cp.custom_terms = new_terms
            self.project.set_custom_profile(cp)
            self.project.save()
            self._load_custom_into_form()

    def _need_project(self) -> bool:
        if not self.project:
            messagebox.showinfo(APP_NAME, "Create or open a project first.")
            return False
        return True

    # ================================================================== files
    def add_files(self):
        paths = filedialog.askopenfilenames(title="Choose documents to sanitize", filetypes=formats.FILE_DIALOG_TYPES)
        self._add_paths(paths)

    def add_folder(self):
        d = filedialog.askdirectory(title="Add every supported file in a folder")
        if d:
            found = []
            for root, _dirs, fs in os.walk(d):
                for f in fs:
                    if formats.is_supported(f) and not f.startswith("~$"):
                        found.append(os.path.join(root, f))
            self._add_paths(found)

    def _add_paths(self, paths):
        added = 0
        for p in paths:
            p = os.path.normpath(p)
            if p not in self.files and formats.is_supported(p):
                self.files.append(p)
                self.file_list.insert("end", os.path.basename(p))
                added += 1
        if added:
            self._reset_review()

    def remove_files(self):
        for i in reversed(self.file_list.curselection()):
            self.file_list.delete(i)
            del self.files[i]
        self._reset_review()

    def clear_files(self):
        self.files.clear()
        self.file_list.delete(0, "end")
        self._reset_review()

    # ================================================================== level
    def _level_changed(self):
        key = self.level.get()
        if self.project:
            p = self.project.profile(key)
            self.project.settings["level"] = key
        else:
            p = next((lv for lv in LEVELS if lv.key == key), None) or self._form_profile()
        self.level_desc.configure(text=p.description)
        cats = ", ".join(CATEGORIES[c].label for c in CATEGORY_ORDER if c in p.categories)
        self.level_cats.configure(text=f"Hides: {cats}")
        self._reset_review()

    # ================================================================== scanning
    def _reset_review(self):
        self.job = None
        if hasattr(self, "tree"):
            self.tree.delete(*self.tree.get_children())
            self.review_count.configure(text="")
            self.btn_apply.configure(state="disabled")
            for w in self.result_frame.winfo_children():
                w.destroy()

    def scan(self):
        if not self._need_project() or self._busy:
            return
        if not self.files:
            messagebox.showinfo(APP_NAME, "Add at least one file first.")
            return
        if self.level.get() == "CUSTOM":
            self.save_custom(silent=True)
        self._save_quick_terms()
        profile = self.project.profile(self.level.get())
        self.job = SanitizeJob(self.project, profile, list(self.files), self.use_ocr.get(), progress=self._progress)
        self._run_bg(self._scan_work, self._scan_done)

    def _scan_work(self):
        self.job.scan()
        # preview the replacements so the user can review them
        self.job.sanitizer.plan()

    def _scan_done(self, err):
        if err:
            messagebox.showerror(APP_NAME, f"Scan failed:\n{err}")
            return
        self._refresh_tree()
        errs = [r for r in self.job.results.values() if r.status == "error"]
        notes = [f"{os.path.basename(r.source)}: {n}" for r in self.job.results.values() for n in r.notes
                 if not n.startswith("Traceback")]
        if errs or notes:
            msg = "\n".join([f"{os.path.basename(r.source)}: {r.error}" for r in errs] + notes)
            messagebox.showwarning(APP_NAME, "Some files need attention:\n\n" + msg)
        self.btn_apply.configure(state="normal" if self.job.extracted else "disabled")
        self.status.set(f"Scan complete - {len(self.job.sanitizer.findings)} sensitive values found. Review, then create copies.")

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        if not self.job:
            return
        flt = self.filter_var.get().lower().strip()
        n_on = 0
        for f in self.job.sanitizer.sorted_findings():
            if f.include:
                n_on += 1
            if flt and flt not in f.original.lower() and flt not in f.category.lower() and flt not in f.replacement.lower():
                continue
            self.tree.insert("", "end", iid=f.key, values=(
                CHECK if f.include else UNCHECK, f.original.replace("\n", " "),
                CATEGORIES[f.category].label if f.category in CATEGORIES else f.category,
                f.replacement if f.include else "(kept as is)", f.count, ", ".join(sorted(f.sources))),
                tags=() if f.include else ("off",))
        total = len(self.job.sanitizer.findings)
        self.review_count.configure(text=f"{n_on} of {total} values will be hidden")

    def _tree_click(self, ev):
        if self.tree.identify_region(ev.x, ev.y) == "cell" and self.tree.identify_column(ev.x) == "#1":
            row = self.tree.identify_row(ev.y)
            if row:
                self._toggle(row)
                return "break"

    def _toggle(self, key, value=None):
        f = self.job.sanitizer.findings.get(key)
        if not f:
            return
        f.include = (not f.include) if value is None else value
        if f.include and not f.replacement:
            e = self.project.vault.replacement_for(f.original, f.category, self.job.profile.style_for(f.category))
            f.replacement = e["replacement"]
        self._update_row(f)

    def _update_row(self, f):
        if self.tree.exists(f.key):
            vals = list(self.tree.item(f.key, "values"))
            vals[0] = CHECK if f.include else UNCHECK
            vals[3] = f.replacement if f.include else "(kept as is)"
            self.tree.item(f.key, values=vals, tags=() if f.include else ("off",))
        n_on = sum(1 for x in self.job.sanitizer.findings.values() if x.include)
        self.review_count.configure(text=f"{n_on} of {len(self.job.sanitizer.findings)} values will be hidden")

    def _toggle_selected(self):
        for k in self.tree.selection():
            self._toggle(k)

    def _set_selected(self, val):
        if self.job:
            for k in self.tree.selection():
                self._toggle(k, val)

    def _tree_double(self, ev):
        row = self.tree.identify_row(ev.y)
        col = self.tree.identify_column(ev.x)
        if not row or col == "#1":
            return
        f = self.job.sanitizer.findings.get(row)
        if not f or not f.include:
            return
        new = simpledialog.askstring(APP_NAME, f"Replace '{f.original}' with:", initialvalue=f.replacement, parent=self)
        if new and new.strip() and new.strip() != f.replacement:
            new = new.strip()
            clash = [e for e in self.project.vault.entries.values() if e["replacement"].lower() == new.lower()
                     and e["original"].lower() != f.original.lower()]
            if clash or new.lower() == f.original.lower():
                messagebox.showerror(APP_NAME, "That replacement is already used (or is the original value) - "
                                               "it must be unique so the answer can be restored.")
                return
            self.project.vault.set_replacement(f.original, new)
            f.replacement = new
            self._update_row(f)
        return "break"

    def _sort_tree(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        rev = getattr(self, "_sort_rev", False)
        try:
            items.sort(key=lambda x: int(x[0]), reverse=rev)
        except ValueError:
            items.sort(key=lambda x: x[0].lower(), reverse=rev)
        for i, (_v, k) in enumerate(items):
            self.tree.move(k, "", i)
        self._sort_rev = not rev

    def add_value(self):
        if not self.job:
            messagebox.showinfo(APP_NAME, "Scan first, then add anything that was missed.")
            return
        d = AddTermDialog(self)
        if not d.result:
            return
        value, cat, remember = d.result
        if cat not in self.job.profile.categories:
            self.job.profile.categories.append(cat)
        self.job.sanitizer.add_manual(value, cat)
        f = self.job.sanitizer.findings.get(norm(value))
        if f:
            f.include = True
            e = self.project.vault.replacement_for(f.original, f.category, self.job.profile.style_for(cat))
            f.replacement = e["replacement"]
        if remember:
            cp = self.project.custom_profile()
            line = value if cat == "CUSTOM" else f"{value} => {cat}"
            if line not in cp.custom_terms:
                cp.custom_terms.append(line)
                self.project.set_custom_profile(cp)
                self.project.save()
                self._load_custom_into_form()
        self._refresh_tree()

    def never_hide(self):
        if not self.job:
            return
        sel = self.tree.selection()
        if not sel:
            return
        cp = self.project.custom_profile()
        for k in sel:
            f = self.job.sanitizer.findings.get(k)
            if f:
                f.include = False
                if f.original not in cp.allow_list:
                    cp.allow_list.append(f.original)
                self._update_row(f)
        self.project.set_custom_profile(cp)
        self.project.save()
        self._load_custom_into_form()

    # ================================================================== apply
    def apply(self):
        if not self.job or self._busy:
            return
        if not any(f.include for f in self.job.sanitizer.findings.values()):
            if not messagebox.askyesno(APP_NAME, "Nothing is selected to hide. Create copies anyway?"):
                return
        self._run_bg(lambda: setattr(self, "_report", self.job.apply()), self._apply_done)

    def _apply_done(self, err):
        for w in self.result_frame.winfo_children():
            w.destroy()
        if err:
            messagebox.showerror(APP_NAME, f"Sanitizing failed:\n{err}")
            return
        self.btn_apply.configure(state="normal")
        res = list(self.job.results.values())
        ok = [r for r in res if r.status == "ok"]
        leaks = [r for r in ok if r.leaks]
        total = sum(r.replaced for r in res)
        style = "Bad.TLabel" if leaks or len(ok) < len(res) else "Ok.TLabel"
        msg = f"✔ {len(ok)} of {len(res)} file(s) sanitized - {total} replacements."
        if leaks:
            msg += f"  ⚠ Leak check found leftovers in {len(leaks)} file(s) - see report."
        failed = [r for r in res if r.status != "ok"]
        if failed:
            msg += "  Failed: " + ", ".join(os.path.basename(r.source) for r in failed)
        ttk.Label(self.result_frame, text=msg, style=style, wraplength=520).pack(side="left")
        ttk.Button(self.result_frame, text="Open report", command=lambda: open_path(self._report)).pack(side="right")
        ttk.Button(self.result_frame, text="Open sanitized folder", style="Accent.TButton",
                   command=lambda: open_path(self.project.sanitized_dir)).pack(side="right", padx=6)
        self._refresh_tree()
        self._refresh_vault()
        self.status.set(f"Done. Sanitized copies are in {self.project.sanitized_dir}")

    # ================================================================== restore
    def _paste_ai(self):
        try:
            self.ai_text.insert("insert", self.clipboard_get())
        except tk.TclError:
            pass

    def do_restore_text(self):
        if not self._need_project():
            return
        text = self.ai_text.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showinfo(APP_NAME, "Paste the AI's response into the left box first.")
            return
        out, n = restore_text(self.project, text)
        self.real_text.delete("1.0", "end")
        self.real_text.insert("1.0", out)
        # highlight restored values
        originals = sorted({e["original"] for e in self.project.vault.entries.values()}, key=len, reverse=True)
        for o in originals[:2000]:
            start = "1.0"
            while True:
                pos = self.real_text.search(o, start, stopindex="end", nocase=True)
                if not pos:
                    break
                end = f"{pos}+{len(o)}c"
                self.real_text.tag_add("hit", pos, end)
                start = end
        self.restore_info.configure(text=f"✔ {n} value(s) restored")

    def do_restore_file(self):
        if not self._need_project():
            return
        path = filedialog.askopenfilename(title="Choose the file returned by the AI", filetypes=formats.FILE_DIALOG_TYPES)
        if not path:
            return
        try:
            out, n, _notes = restore_file(self.project, path)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not restore the file:\n{exc}")
            return
        self.restore_info.configure(text=f"✔ {n} value(s) restored -> {os.path.basename(out)}")
        if messagebox.askyesno(APP_NAME, f"Restored {n} value(s).\n\nSaved as:\n{out}\n\nOpen it now?"):
            open_path(out)

    def _copy_real(self):
        self.clipboard_clear()
        self.clipboard_append(self.real_text.get("1.0", "end-1c"))
        self.restore_info.configure(text="✔ Copied to clipboard")

    def _save_real(self):
        if not self.project:
            return
        p = filedialog.asksaveasfilename(initialdir=self.project.restored_dir, defaultextension=".txt",
                                         filetypes=[("Text", "*.txt"), ("Markdown", "*.md")])
        if p:
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(self.real_text.get("1.0", "end-1c"))

    # ================================================================== custom
    def _form_profile(self) -> Profile:
        cats = [c for c in CATEGORY_ORDER if self.cat_vars[c].get()]
        style = {c: (REALISTIC if self.style_vars[c].get() == "Realistic" else TOKEN) for c in CATEGORY_ORDER}
        lines = lambda w: [x.strip() for x in w.get("1.0", "end").splitlines() if x.strip()]  # noqa: E731
        return Profile("CUSTOM", "Custom", "Your own combination",
                       "Your own selection of categories, replacement styles, terms and patterns.",
                       cats, style, self.strip_meta.get(), lines(self.terms_text), lines(self.allow_text),
                       lines(self.pattern_text))

    def _load_custom_into_form(self):
        if not self.project:
            return
        p = self.project.custom_profile()
        self.quick_terms.set(", ".join(t.split("=>", 1)[0].strip() for t in p.custom_terms if self._is_org_term(t)))
        for c in CATEGORY_ORDER:
            self.cat_vars[c].set(c in p.categories)
            self.style_vars[c].set("Realistic" if p.style_for(c) == REALISTIC and CATEGORIES[c].can_be_realistic else "Placeholder")
        self.strip_meta.set(p.strip_metadata)
        for w, vals in ((self.terms_text, p.custom_terms), (self.allow_text, p.allow_list), (self.pattern_text, p.custom_patterns)):
            w.delete("1.0", "end")
            w.insert("1.0", "\n".join(vals))

    def _custom_from(self, lvl: Profile):
        for c in CATEGORY_ORDER:
            self.cat_vars[c].set(c in lvl.categories)
            st = lvl.style_for(c)
            self.style_vars[c].set("Realistic" if st == REALISTIC and CATEGORIES[c].can_be_realistic else "Placeholder")
        self.strip_meta.set(lvl.strip_metadata)

    def save_custom(self, silent=False):
        if not self._need_project():
            return
        from .detectors import parse_custom_patterns
        p = self._form_profile()
        _pats, errors = parse_custom_patterns(p.custom_patterns)
        if errors and not silent:
            messagebox.showerror(APP_NAME, "These patterns are not valid regular expressions:\n\n" + "\n".join(errors))
            return
        self.project.set_custom_profile(p)
        self.project.save()
        self._level_changed()
        if not silent:
            self.status.set("Custom settings saved to the project.")
            messagebox.showinfo(APP_NAME, "Custom settings saved. Your terms and never-hide list apply to every level; "
                                          "the category choices apply when 'Custom' is selected.")

    # ================================================================== vault
    def _refresh_vault(self):
        self.vtree.delete(*self.vtree.get_children())
        if not self.project:
            return
        flt = self.vault_filter.get().lower().strip()
        entries = self.project.vault.entries
        for k, e in sorted(entries.items(), key=lambda kv: (kv[1]["category"], kv[0])):
            if flt and flt not in k and flt not in e["replacement"].lower():
                continue
            self.vtree.insert("", "end", iid=k, values=(e["original"], e["category"], e["replacement"],
                                                         e.get("created", "").replace("T", " ")))
        lock = "password protected" if self.project.password else "NOT password protected"
        self.vault_info.configure(text=f"{len(entries)} mappings - {lock}")

    def vault_delete(self):
        sel = self.vtree.selection()
        if not sel or not messagebox.askyesno(APP_NAME, f"Delete {len(sel)} mapping(s)? AI answers that use them "
                                                         "can then no longer be restored."):
            return
        for k in sel:
            self.project.vault.entries.pop(k, None)
        self.project.save()
        self._refresh_vault()

    def change_password(self):
        if not self._need_project():
            return
        pw = simpledialog.askstring(APP_NAME, "New vault password (leave empty to remove protection):", show="•", parent=self)
        if pw is None:
            return
        if pw:
            pw2 = simpledialog.askstring(APP_NAME, "Repeat the new password:", show="•", parent=self)
            if pw2 != pw:
                messagebox.showerror(APP_NAME, "Passwords do not match.")
                return
        self.project.password = pw or None
        self.project.save()
        self._project_loaded()

    # ================================================================== settings
    def locate_tesseract(self):
        p = filedialog.askopenfilename(title="Locate tesseract.exe", filetypes=[("tesseract", "tesseract*.exe"), ("All", "*.*")])
        if p:
            ocr.set_tesseract_path(p)
            self.cfg["tesseract_path"] = p
            config.save(self.cfg)
            self._update_ocr_status()

    def _update_ocr_status(self):
        path = ocr.find_tesseract()
        if path and ocr.available():
            self.ocr_status.configure(text=f"✔ Tesseract found: {path}", style="Ok.TLabel")
            self.ocr_check.configure(text="Use OCR for images and scanned PDFs")
        else:
            self.ocr_status.configure(text="✖ Tesseract OCR not found - images and scanned PDFs cannot be read.",
                                      style="Bad.TLabel")
            self.ocr_check.configure(text="Use OCR for images and scanned PDFs (Tesseract not installed - see Settings)")

    def _tab_changed(self):
        if self.nb.select() == str(self.tab_vault):
            self._refresh_vault()

    # ================================================================== threading
    def _progress(self, msg, frac=None):
        self.q.put(("progress", msg, frac))

    def _run_bg(self, work, done):
        self._busy = True
        self.btn_scan.configure(state="disabled")
        self.btn_apply.configure(state="disabled")
        self.configure(cursor="watch")

        def runner():
            err = None
            try:
                work()
            except Exception as exc:
                err = f"{exc}\n\n{traceback.format_exc(limit=3)}"
            self.q.put(("done", done, err))

        threading.Thread(target=runner, daemon=True).start()

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item[0] == "progress":
                    _, msg, frac = item
                    self.status.set(msg)
                    if frac is not None:
                        self.progress["value"] = frac * 100
                elif item[0] == "done":
                    _, done, err = item
                    self._busy = False
                    self.configure(cursor="")
                    self.btn_scan.configure(state="normal")
                    self.progress["value"] = 0
                    done(err)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _close(self):
        if self._busy and not messagebox.askyesno(APP_NAME, "Work is still running. Quit anyway?"):
            return
        try:
            if self.project and self.project.vault.dirty:
                self.project.save()
        except Exception:
            pass
        self.destroy()


def main():
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    App().mainloop()


if __name__ == "__main__":
    main()
