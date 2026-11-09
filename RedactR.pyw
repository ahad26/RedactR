"""Launcher for ЯedactR.

Double-click (or RedactR.exe with no arguments) opens the desktop app.
With arguments it runs the command line, e.g.:
    RedactR.exe sanitize --project "D:\\Q3" --create --level L3 report.docx
    RedactR.exe restore  --project "D:\\Q3" --file answer.docx
"""
import os
import sys

if not getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from redactr import splash  # noqa: E402


def load_gui():
    """Import the heavy parts up front, telling the user on the splash screen what is loading."""
    steps = [
        ("Loading interface toolkit...", lambda: __import__("tkinter.ttk")),
        ("Loading Word, Excel & PowerPoint engine...", lambda: __import__("redactr.ooxml")),
        ("Loading PDF engine...", lambda: __import__("pymupdf")),
        ("Loading image tools...", lambda: __import__("PIL.ImageDraw")),
        ("Loading vault encryption (AES)...", lambda: __import__("cryptography.fernet")),
        ("Loading detection rules: names, IDs, finance, secrets...", lambda: __import__("redactr.engine")),
    ]
    for message, step in steps:
        splash.update(message)
        step()
    splash.update("Checking OCR engine...")
    from redactr import ocr
    splash.update("OCR engine ready (Tesseract)" if ocr.find_tesseract() else "OCR engine not found - continuing without OCR")
    splash.update("Building the workspace...")
    from redactr.gui import main
    return main


if len(sys.argv) > 1 and sys.argv[1] in ("sanitize", "restore", "-h", "--help"):
    splash.close()
    from redactr.cli import main as cli_main
    cli_main()
else:
    try:
        load_gui()()
    except Exception as exc:  # never leave a splash hanging with no explanation
        splash.close()
        import traceback
        import tkinter.messagebox as mb
        mb.showerror("ЯedactR", f"ЯedactR could not start:\n\n{exc}\n\n{traceback.format_exc(limit=3)}")
        raise
