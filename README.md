# ЯedactR

**Clean confidential documents on your own computer before you upload them to an AI chatbot, then put the real values back into the AI's answer.**

ЯedactR is a Windows desktop app. It does not run in a browser, it has no server and it makes no network calls. Detection, replacement, OCR, encryption and restoring all happen on this PC.

```
 your files ──► ЯedactR ──► sanitized copies ──► AI chatbot
                  │                                   │
             mapping vault ◄──────── AI answer ◄──────┘
                  │
                  └──► restored answer with the real names
```

## Supported files

| Type | Formats | What gets cleaned |
|---|---|---|
| Word | .docx .docm (.doc .rtf .odt are converted locally) | Body, tables, headers and footers, footnotes, comments, tracked changes and their authors, text boxes, SmartArt, hyperlinks, properties, embedded Excel files |
| Excel | .xlsx .xlsm .csv (.xls .ods are converted locally) | Cells, sheet names (formulas are fixed to match), comments, headers and footers, charts, pivot caches, table headers, properties. Column headers give extra hints, so everything under a "Name", "Email", "Salary" or "SSN" column is treated as that type |
| PowerPoint | .pptx .pptm (.ppt .odp are converted locally) | Slides, tables, speaker notes, layouts and masters, charts, comment authors, properties |
| PDF | .pdf | Text pages are rewritten in reading order. Scanned pages go through OCR and are redacted in the image. Links, bookmarks and metadata are cleaned too |
| Images | .png .jpg .tif .bmp .gif .webp | OCR finds the sensitive words, which are painted over and relabelled. You also get a `.txt` copy of the text. EXIF and GPS data is removed |
| Text | .txt .md .json .xml .html .log .eml | All of the text |

Legacy formats (.doc, .xls, .ppt) are converted with Microsoft Office or LibreOffice, using whichever is installed.

## The five levels plus Custom

| Level | Name | What it hides | Replaced with |
|---|---|---|---|
| 1 | **Alias** | People's names | Consistent fictional names (Sarah Johnson → Wystan Zellner) |
| 2 | **Private** | Level 1, plus emails, phone numbers, street addresses, SSN and national IDs, payment cards, dates of birth, passwords and API keys | Safe fictional contacts (`*.example` domains, 555-01xx numbers). Identifiers become `[NATIONAL_ID_1]` |
| 3 | **Confidential** | Level 2, plus company, client and vendor names, locations, URLs, IP and MAC addresses, bank accounts, internal IDs and your custom terms. Document metadata is wiped | Fictional companies and cities, plus placeholders |
| 4 | **Restricted** | Level 3, plus money amounts, all dates, percentages and file paths | `[AMOUNT_2]`, `[DATE_5]` and similar |
| 5 | **Top Secret** | Level 4, plus every remaining number and capitalised proper noun | Placeholders only (`[PERSON_1]`, `[ORG_2]`, `[NUM_7]`) |
| – | **Custom** | You choose the categories and pick realistic or placeholder replacement for each. You can add your own terms, a never-hide list and regex patterns | Your choice |

The same real value always gets the same replacement within a project. Surnames and first names stay linked too: if the AI writes "Mr. Zellner", ЯedactR restores it to "Mr. Johnson".

## Portable app (recommended)

There are two portable versions. Both contain everything: Python, all libraries and the Tesseract OCR engine for images and scanned PDFs (English). Neither needs installing or admin rights, and both work on any Windows 10 or 11 PC.

| Version | What you copy | Start-up | Best for |
|---|---|---|---|
| **Single file** | `dist\RedactR.exe` (about 124 MB) | about 15 s | Emailing or carrying one file around |
| **Fast start** | `dist\RedactR-Fast.zip`, unzipped anywhere, then run `RedactR-Fast\RedactR.exe` | a few seconds | Everyday use on a PC or network share |

The fast-start version is the same app, already unpacked. Keep the `_internal` folder next to its `RedactR.exe`.

- A splash screen appears within about a second and shows what is loading: first each file the exe unpacks (single-file version only), then the PDF engine, OCR, detection rules and so on.
- **Company names:** type your own company's and your clients' names into *Company & client names to always hide* on the Sanitize tab, for example `Globex, Initech`. They are hidden at every level, including 1 and 2, and saved with the project. From Level 3 upwards, names are also found automatically. ЯedactR looks for legal suffixes (Inc, LLC…), brand-shaped words (GlobexCorp, X-CORP, AT&T), names that match an email or web domain in the documents (`@globexcorp.com` → "GlobexCorp"), and the document's *Company* property. Different spellings of the same company (X-CORP, XCORP) get the same fictional name.
- Your projects live wherever you create them. The only other thing it writes is a small settings file in `%APPDATA%\RedactR`.
- It also works from the command line: `RedactR.exe sanitize --project D:\Q3 --create --level L3 file.docx` and `RedactR.exe restore --project D:\Q3 --file answer.docx`. Add `--password` for scripted runs.
- **OCR is built in.** Scanned PDF pages have the sensitive words blanked out of the image, the replacements drawn in, and an invisible text layer added, so AI tools can read the cleaned page as text. Images get the same blanking plus a `.txt` copy of their text.
- **Other OCR languages:** install the language in Tesseract, add its code to `LANGS` in `packaging\prepare_tesseract.py`, and rebuild.
- To rebuild the exe after changing the code, run `build_exe.bat`. If Tesseract is installed on the build PC, it is bundled automatically (only the ~120 MB it actually needs).
- Tesseract is Apache-2.0 licensed. Its licence files are bundled inside the exe.
- Windows may show a SmartScreen warning the first time, because the exe isn't code-signed. Choose *More info → Run anyway*, or sign it with your company's code-signing certificate.
- The exe is Windows only. For Mac or Linux, build it on that system with the same `packaging\RedactR.spec`.

## Running from source

1. You need **Python 3.10 or newer** from <https://www.python.org/downloads/>.
2. Double-click **`Start RedactR.bat`**. The first run sets up a private environment, which takes about a minute. Later runs start the app straight away.
3. Optional, for images and scanned PDFs: install the free Tesseract OCR engine:
   ```bash
   winget install UB-Mannheim.TesseractOCR
   ```
   Restart ЯedactR after installing. If it doesn't find Tesseract, go to Settings & help and use *Locate tesseract.exe*.

**Deploying to colleagues without Python:** give them `dist\RedactR.exe` (see *Portable app* above).

## How to use it

1. **New project**: create one per client, case or piece of work, and set a vault password.
2. **Sanitize tab**: add your files, pick a level and press **Scan for sensitive data**.
3. **Review the table**: untick anything that should stay, double-click a replacement to change it, and use *Add value* for anything that was missed. Add client names and project code names under **Custom level & terms**. That list applies to every level and is always caught.
4. Press **Create sanitized copies**. Upload **only** the files in the project's `sanitized` folder.
5. **Open the report.** The HTML, JSON and CSV versions show every original value, what replaced it, how often and in which files. Each file also gets a **leak check**: the written copy is read back to confirm that no original value survived.
6. When the AI answers, go to **Restore AI response**. Paste the answer and press **Restore text**, or use **Restore a file…** for a document the AI produced. The fictional values are swapped back to the real ones and highlighted.

### Project folder layout
```
My Project\
  redactr-project.json         settings, custom terms
  mapping.redactr-vault        real ↔ fictional mapping (AES encrypted with your password)
  sanitized\                   ← upload these
  reports\                     what was removed (CONFIDENTIAL – keep local)
  restored\                    AI output with the real values back
```

## Command line (batch use)
```bash
.venv\Scripts\python -m redactr.cli sanitize --project "D:\RedactR\Q3" --create --level L3 file1.docx deck.pptx
```
```bash
.venv\Scripts\python -m redactr.cli restore --project "D:\RedactR\Q3" --file ai_answer.docx
```
```bash
.venv\Scripts\python -m redactr.cli restore --project "D:\RedactR\Q3" --text "Wystan Zellner should call Riverstone Corporation"
```
You can pass the vault password with `--password` or the `REDACTR_PASSWORD` environment variable. If you don't, you're prompted for it.

## Limits

- Detection uses rules: patterns, checksums, name dictionaries, context and column headers. No AI model is involved, so it is strong but not perfect. **Always review the table before uploading** and keep your custom term list up to date.
- Pictures embedded inside Word or PowerPoint files are left unchanged. The report warns you when a file contains them.
- Restoring only works for values the AI repeats as they were given. If the AI paraphrases a name, for example by using a nickname, restore that part by hand. The vault tab shows every mapping.
- Money and dates are replaced with placeholders, not fake numbers. Any totals the AI calculates from placeholders need checking against the real figures.
- In PDFs, a changed page is redrawn with standard fonts, so its layout can differ slightly from the original.
- Keep the vault and reports private. Anyone who has them can reverse the sanitization.

## Try it
```bash
.venv\Scripts\python samples\make_samples.py
```
This creates made-up confidential sample files in `samples\input`.
