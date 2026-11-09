# PyInstaller spec - builds one portable RedactR.exe (no install, no Python needed).
# Build with:  build_exe.bat   (or: python -m PyInstaller packaging\RedactR.spec)
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

DATAS = [(os.path.join(ROOT, "redactr", "assets"), "redactr/assets")]
# Bundled OCR engine (prepared by packaging\prepare_tesseract.py). Unpacked next to the app at run time.
TESS = os.path.join(SPECPATH, "tesseract")
if os.path.isfile(os.path.join(TESS, "tesseract.exe")):
    DATAS.append((TESS, "tesseract"))
    print("Bundling Tesseract OCR from", TESS)
else:
    print("WARNING: packaging\\tesseract not found - building without OCR")

a = Analysis(
    [os.path.join(ROOT, "RedactR.pyw")],
    pathex=[ROOT],
    datas=DATAS,
    hiddenimports=["redactr.cli", "redactr.gui", "pytesseract", "lxml.etree", "lxml._elementpath",
                   "cryptography.hazmat.primitives.kdf.pbkdf2"],
    excludes=[
        # pulled in by optional PyMuPDF add-ons / test tooling - not needed, saves ~100 MB
        "pymupdf4llm", "pymupdf_layout", "onnxruntime", "numpy", "networkx", "tabulate",
        "matplotlib", "pandas", "scipy", "IPython", "pytest", "unittest", "pydoc_data",
    ],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

# Start-up splash: shown by the bootloader immediately, while the exe unpacks itself.
# The bootloader writes the name of each file being unpacked into the text area; once Python
# runs, redactr.splash replaces it with the app's own loading steps.
splash = Splash(
    os.path.join(SPECPATH, "splash.png"),
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(48, 303),
    text_size=10,
    text_font="{Segoe UI}",          # Tcl braces: PyInstaller inserts the name unquoted
    text_color="#C9C3E3",
    text_default="Starting RedactR...",
    minify_script=True,
    always_on_top=True,
)

EXE_OPTS = dict(
    name="RedactR",
    icon=os.path.join(ROOT, "packaging", "redactr.ico"),
    version=os.path.join(ROOT, "packaging", "version_info.txt"),
    console=False,
    upx=False,
)

# REDACTR_BUILD=folder -> fast-start folder (RedactR-Fast\RedactR.exe + _internal\), nothing to unpack at launch.
# default             -> one self-contained RedactR.exe that unpacks itself on every start.
if os.environ.get("REDACTR_BUILD", "").lower() == "folder":
    exe = EXE(pyz, a.scripts, splash, [], exclude_binaries=True, **EXE_OPTS)
    coll = COLLECT(exe, a.binaries, a.datas, splash.binaries, upx=False, name="RedactR-Fast")
else:
    exe = EXE(pyz, a.scripts, splash, splash.binaries, a.binaries, a.datas, [], runtime_tmpdir=None, **EXE_OPTS)
