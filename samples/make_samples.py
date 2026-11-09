"""Generate fake 'confidential' sample files for trying ЯedactR.
All people, companies and numbers below are made up."""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "input")
os.makedirs(OUT, exist_ok=True)

MEMO = """CONFIDENTIAL MEMO
From: Sarah Johnson, CFO, Acme Widgets Inc.
To: Mr. David Chen
Date: March 3, 2024

Dear David,
Following our call with Globex Corporation, Sarah approved a revised budget of $1,250,000 (up 12.5%).
Please contact Priya Sharma at priya.sharma@acmewidgets.com or +1 (415) 555-2671 before Friday.
Our Chicago office (742 Evergreen Terrace, Springfield, IL 62704) will host the kickoff for Project Falcon.
Payroll account: IBAN GB82 WEST 1234 5698 7654 32. Employee ID: EMP-20391. SSN 219-09-9999.
VPN host 10.0.4.17, password: Hunter2!x. Draft stored at C:\\Shares\\Finance\\Falcon.docx.
Regards,
Sarah Johnson
"""


def make_txt():
    with open(os.path.join(OUT, "memo.txt"), "w", encoding="utf-8") as fh:
        fh.write(MEMO)


def make_docx():
    from docx import Document
    d = Document()
    d.core_properties.author = "Sarah Johnson"
    d.core_properties.title = "Falcon budget - Acme Widgets Inc."
    d.sections[0].header.paragraphs[0].text = "Acme Widgets Inc. - prepared by Sarah Johnson"
    d.add_heading("Project Falcon - Budget Review", 1)
    p = d.add_paragraph("Meeting between ")
    p.add_run("Sarah").bold = True
    p.add_run(" Johnson").italic = True
    p.add_run(" and Michael Brown of Globex Corporation on 12/05/2024. Contact michael.brown@globex.com.")
    d.add_paragraph("Michael asked for the revised forecast of $2.4M by Friday. Call him at (312) 555-0198.")
    t = d.add_table(rows=4, cols=4)
    for r, row in enumerate([["Name", "Email", "Phone", "Salary"],
                             ["Emily Carter", "emily.carter@acmewidgets.com", "212-555-0143", "$145,000"],
                             ["Rajesh Kumar", "rkumar@acmewidgets.com", "646-555-0112", "$132,500"],
                             ["Laura Nguyen", "laura.n@acmewidgets.com", "917-555-0177", "$128,000"]]):
        for c, v in enumerate(row):
            t.cell(r, c).text = v
    d.add_paragraph("Account Number: 0012 3456 7890, routing 021000021.")
    d.save(os.path.join(OUT, "budget_review.docx"))


def make_xlsx():
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Payroll"
    ws.append(["Employee Name", "Employee ID", "Email", "Department", "Salary", "Start Date"])
    rows = [("John Smith", "EMP-1001", "john.smith@acmewidgets.com", "Finance", 98000, "2019-04-01"),
            ("Maria Garcia", "EMP-1002", "maria.garcia@acmewidgets.com", "Sales", 87000, "2020-07-15"),
            ("Ahmed Khan", "EMP-1003", "ahmed.khan@acmewidgets.com", "Engineering", 121000, "2018-11-30"),
            ("Olivia Wilson", "EMP-1004", "olivia.wilson@acmewidgets.com", "Legal", 134000, "2021-02-01")]
    for r in rows:
        ws.append(list(r))
    ws["G1"] = "Total"
    ws["G2"] = "=SUM(E2:E5)"
    ws2 = wb.create_sheet("Clients")
    ws2.append(["Company", "Contact", "Phone", "City"])
    ws2.append(["Globex Corporation", "Michael Brown", "(312) 555-0198", "Chicago"])
    ws2.append(["Initech LLC", "Bill Lumbergh", "(512) 555-0110", "Austin"])
    ws2["E1"] = "=Payroll!E2"
    wb.properties.creator = "Sarah Johnson"
    wb.save(os.path.join(OUT, "payroll.xlsx"))


def make_pptx():
    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = "Project Falcon - Acme Widgets Inc."
    s.placeholders[1].text = ("Presented by Sarah Johnson\nClient: Globex Corporation\n"
                              "Budget $1,250,000 approved on March 3, 2024")
    s.notes_slide.notes_text_frame.text = "Remind David Chen about the SSN list (219-09-9999)."
    s2 = prs.slides.add_slide(prs.slide_layouts[5])
    s2.shapes.title.text = "Team"
    tbl = s2.shapes.add_table(3, 2, Inches(1), Inches(2), Inches(6), Inches(1.5)).table
    for r, (a, b) in enumerate([("Name", "Email"), ("Emily Carter", "emily.carter@acmewidgets.com"),
                                ("Rajesh Kumar", "rkumar@acmewidgets.com")]):
        tbl.cell(r, 0).text, tbl.cell(r, 1).text = a, b
    prs.core_properties.author = "Sarah Johnson"
    prs.save(os.path.join(OUT, "falcon_deck.pptx"))


def make_pdf():
    import pymupdf as fitz
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in MEMO.splitlines():
        page.insert_text((72, y), line, fontsize=10, fontname="helv")
        y += 16
    doc.set_metadata({"author": "Sarah Johnson", "title": "Falcon memo"})
    doc.save(os.path.join(OUT, "memo.pdf"))


def make_scanned_pdf():
    """The memo as a picture-only PDF (like a scanner produces) - needs OCR."""
    import pymupdf
    src = pymupdf.open(os.path.join(OUT, "memo.pdf"))
    pix = src[0].get_pixmap(dpi=200)
    doc = pymupdf.open()
    page = doc.new_page(width=src[0].rect.width, height=src[0].rect.height)
    page.insert_image(page.rect, pixmap=pix)
    doc.save(os.path.join(OUT, "memo_scanned.pdf"))


def make_png():
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1400, 420), "white")
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("arial.ttf", 34)
    except OSError:
        f = ImageFont.load_default()
    lines = ["Invoice for Globex Corporation", "Attention: Michael Brown",
             "Email: michael.brown@globex.com  Phone: (312) 555-0198", "Amount due: $48,250.00"]
    for i, l in enumerate(lines):
        d.text((40, 40 + i * 80), l, fill="black", font=f)
    img.save(os.path.join(OUT, "invoice_scan.png"))


def make_csv():
    with open(os.path.join(OUT, "contacts.csv"), "w", encoding="utf-8", newline="") as fh:
        fh.write("Name,Company,Email,Phone\n")
        fh.write("Emily Carter,Acme Widgets Inc.,emily.carter@acmewidgets.com,212-555-0143\n")
        fh.write("Michael Brown,Globex Corporation,michael.brown@globex.com,(312) 555-0198\n")


if __name__ == "__main__":
    for fn in (make_txt, make_docx, make_xlsx, make_pptx, make_pdf, make_scanned_pdf, make_png, make_csv):
        fn()
    print("Sample files written to", OUT)
