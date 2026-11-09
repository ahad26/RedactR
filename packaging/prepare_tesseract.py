"""Copy the minimum set of Tesseract files needed by ЯedactR into packaging/tesseract,
so they can be bundled into the portable exe.

Install Tesseract first (winget install UB-Mannheim.TesseractOCR), then run:
    .venv\\Scripts\\python packaging\\prepare_tesseract.py
Only tesseract.exe, the DLLs it actually loads, English language data and the
output configs are copied (about 120 MB instead of 240 MB).
"""
import os
import shutil
import sys

try:
    import pefile
except ImportError:
    sys.exit("pip install pefile first")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\Program Files\Tesseract-OCR"
DST = os.path.join(HERE, "tesseract")
LANGS = ["eng"]  # add more language codes here (their .traineddata must be installed)

if not os.path.isfile(os.path.join(SRC, "tesseract.exe")):
    sys.exit(f"tesseract.exe not found in {SRC}")

local = {f.lower(): f for f in os.listdir(SRC) if f.lower().endswith(".dll")}
need, todo = set(), ["tesseract.exe"]
while todo:
    name = todo.pop()
    pe = pefile.PE(os.path.join(SRC, local.get(name.lower(), name)), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                                           pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"]])
    for attr in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT"):
        for entry in getattr(pe, attr, []):
            dll = entry.dll.decode().lower()
            if dll in local and dll not in need:
                need.add(dll)
                todo.append(dll)

shutil.rmtree(DST, ignore_errors=True)
os.makedirs(os.path.join(DST, "tessdata"))
shutil.copy2(os.path.join(SRC, "tesseract.exe"), DST)
for dll in sorted(need):
    shutil.copy2(os.path.join(SRC, local[dll]), DST)
for lang in LANGS:
    shutil.copy2(os.path.join(SRC, "tessdata", f"{lang}.traineddata"), os.path.join(DST, "tessdata"))
for d in ("configs", "tessconfigs"):
    shutil.copytree(os.path.join(SRC, "tessdata", d), os.path.join(DST, "tessdata", d))
for f in ("LICENSE", "AUTHORS"):
    for cand in (os.path.join(SRC, "doc", f), os.path.join(SRC, f)):
        if os.path.isfile(cand):
            shutil.copy2(cand, os.path.join(DST, f"TESSERACT_{f}.txt"))
            break
size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(DST) for f in fs)
print(f"Prepared {DST}: tesseract.exe + {len(need)} DLLs + {', '.join(LANGS)} ({size / 1e6:.0f} MB)")
