"""Zip dist/RedactR-Fast -> dist/RedactR-Fast.zip, retrying files that antivirus briefly locks after a build."""
import os
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "dist", "RedactR-Fast")
DST = os.path.join(ROOT, "dist", "RedactR-Fast.zip")

tmp = DST + ".tmp"
with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for base, _dirs, files in os.walk(SRC):
        for f in files:
            path = os.path.join(base, f)
            arc = os.path.relpath(path, os.path.dirname(SRC))
            for attempt in range(30):
                try:
                    z.write(path, arc)
                    break
                except PermissionError:
                    time.sleep(1)
            else:
                raise SystemExit(f"still locked after 30 s: {path}")
os.replace(tmp, DST)
print(f"wrote {DST} ({os.path.getsize(DST) / 1e6:.0f} MB)")
