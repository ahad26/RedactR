# Third-party notices

ЯedactR is licensed under the **GNU Affero General Public License v3.0** (see [LICENSE](LICENSE)).
The complete source code is available at <https://github.com/ahad26/RedactR>.

The portable Windows builds (`RedactR.exe`, `RedactR-Fast.zip`) include the open-source
components listed below. Each component remains under its own licence, and their copyright
belongs to their respective authors. The licence names here are a summary. The full licence
texts are distributed with each upstream project; follow the links for details.

## Python libraries

| Component | Used for | Licence | Project |
|---|---|---|---|
| CPython | runtime | PSF License 2.0 | https://www.python.org |
| Tcl/Tk (tkinter) | desktop interface, splash screen | Tcl/Tk License (BSD-style) | https://www.tcl.tk |
| PyMuPDF / MuPDF | reading and writing PDF files | **GNU AGPL-3.0** (or Artifex commercial licence) | https://github.com/pymupdf/PyMuPDF |
| lxml (libxml2, libxslt) | Office XML processing | BSD-3-Clause (libxml2 / libxslt: MIT) | https://lxml.de |
| Pillow | images and OCR overlays | MIT-CMU (HPND) | https://python-pillow.org |
| cryptography (OpenSSL) | encrypted mapping vault | Apache-2.0 or BSD-3-Clause (OpenSSL: Apache-2.0) | https://cryptography.io |
| pytesseract | OCR bridge | Apache-2.0 | https://github.com/madmaze/pytesseract |
| PyInstaller bootloader | packaging the executable | GPL-2.0-or-later with bootloader exception | https://pyinstaller.org |

### Used only by the developer tools (not included in the executables)

| Component | Used for | Licence | Project |
|---|---|---|---|
| python-docx | generating sample Word files | MIT | https://github.com/python-openxml/python-docx |
| python-pptx | generating sample PowerPoint files | MIT | https://github.com/scanny/python-pptx |
| openpyxl | generating sample Excel files | MIT | https://foss.heptapod.net/openpyxl/openpyxl |
| imageio-ffmpeg (FFmpeg) | rendering the demo video | BSD-2-Clause (FFmpeg: LGPL/GPL) | https://github.com/imageio/imageio-ffmpeg |
| pefile | trimming the Tesseract bundle | MIT | https://github.com/erocarrera/pefile |

## OCR engine (bundled Tesseract build)

The OCR engine is the Windows build of Tesseract published by UB Mannheim
(https://github.com/UB-Mannheim/tesseract). Its licence and author list are also included inside the
app as `tesseract/TESSERACT_LICENSE.txt` and `tesseract/TESSERACT_AUTHORS.txt`.

| Component | Licence | Project |
|---|---|---|
| Tesseract OCR (+ English language data) | Apache-2.0 | https://github.com/tesseract-ocr/tesseract |
| Leptonica | BSD-2-Clause | http://www.leptonica.org |
| libarchive | BSD-2-Clause | https://www.libarchive.org |
| OpenSSL (libcrypto) | Apache-2.0 | https://www.openssl.org |
| libpng | libpng License | http://www.libpng.org |
| zlib | zlib License | https://zlib.net |
| libjpeg-turbo | IJG License / BSD-3-Clause | https://libjpeg-turbo.org |
| libtiff | libtiff License (BSD-style) | https://libtiff.gitlab.io/libtiff |
| libwebp, libwebpmux, libsharpyuv | BSD-3-Clause | https://chromium.googlesource.com/webm/libwebp |
| OpenJPEG | BSD-2-Clause | https://www.openjpeg.org |
| giflib | MIT | https://giflib.sourceforge.net |
| JBIG-KIT (libjbig) | GPL-2.0-or-later | https://www.cl.cam.ac.uk/~mgk25/jbigkit |
| LERC | Apache-2.0 | https://github.com/Esri/lerc |
| libdeflate | MIT | https://github.com/ebiggers/libdeflate |
| Zstandard (libzstd) | BSD-3-Clause | https://github.com/facebook/zstd |
| LZ4 | BSD-2-Clause | https://github.com/lz4/lz4 |
| XZ Utils (liblzma) | 0BSD / public domain | https://tukaani.org/xz |
| bzip2 | bzip2 License (BSD-style) | https://sourceware.org/bzip2 |
| BLAKE2 (libb2) | CC0-1.0 / Apache-2.0 | https://github.com/BLAKE2/libb2 |
| Expat | MIT | https://libexpat.github.io |
| GNU libiconv | LGPL-2.1-or-later | https://www.gnu.org/software/libiconv |
| GCC runtime (libgcc, libstdc++) | GPL-3.0 with GCC Runtime Library Exception | https://gcc.gnu.org |
| mingw-w64 winpthreads | MIT / ZPL-2.1 | https://www.mingw-w64.org |

GPL-2.0-or-later (JBIG-KIT) and LGPL-2.1-or-later (libiconv) components can be combined with
AGPL-3.0 software. If you believe a notice here is incomplete or inaccurate, please
[open an issue](https://github.com/ahad26/RedactR/issues).
