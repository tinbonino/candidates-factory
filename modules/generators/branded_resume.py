"""
Generates the anonymized Stefanini/LDH branded resume PDF.
Anonymization: last name reduced to initial, no contact info.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
    Table, TableStyle, Flowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER

BLUE      = colors.HexColor("#003087")
ORANGE    = colors.HexColor("#FF6B00")
LIGHT_GRAY= colors.HexColor("#F5F5F5")
MID_GRAY  = colors.HexColor("#666666")
WHITE     = colors.white

W, H   = A4
MARGIN = 20 * mm


class _ColorBar(Flowable):
    def __init__(self, width, height, color):
        super().__init__()
        self.width  = width
        self.height = height
        self.color  = color

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)


def _header(story, candidate, logo_path):
    story.append(_ColorBar(W - 2 * MARGIN, 4 * mm, ORANGE))
    story.append(Spacer(1, 3 * mm))

    name_style = ParagraphStyle(
        "rname", fontName="Helvetica-Bold", fontSize=20,
        textColor=BLUE, leading=24
    )
    title_style = ParagraphStyle(
        "rtitle", fontName="Helvetica", fontSize=12,
        textColor=ORANGE, leading=16
    )
    yoe_style = ParagraphStyle(
        "ryoe", fontName="Helvetica", fontSize=9,
        textColor=MID_GRAY, leading=12
    )

    if logo_path and os.path.exists(logo_path):
        from reportlab.platypus import Image
        from reportlab.lib.utils import ImageReader

        # Compute logo dimensions preserving exact aspect ratio
        try:
            ir = ImageReader(logo_path)
            iw_px, ih_px = ir.getSize()
            aspect = iw_px / ih_px
        except Exception:
            aspect = 4.0   # fallback wide landscape ratio

        logo_h = 16 * mm
        logo_w = logo_h * aspect
        # Cap so it doesn't overflow: leave at least 70 mm for the name
        content_w = W - 2 * MARGIN
        max_logo_w = content_w - 70 * mm
        logo_w = min(logo_w, max_logo_w)

        logo      = Image(logo_path, width=logo_w, height=logo_h)
        name_para = Paragraph(candidate.display_name, name_style)
        logo_col  = logo_w + 4 * mm
        name_col  = content_w - logo_col

        tbl = Table(
            [[name_para, logo]],
            colWidths=[name_col, logo_col],
        )
        tbl.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("ALIGN",        (1, 0), (1, 0),   "RIGHT"),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph(candidate.display_name, name_style))

    story.append(Paragraph(candidate.title or "", title_style))
    if candidate.years_of_experience:
        story.append(
            Paragraph(f"{candidate.years_of_experience} years of experience", yoe_style)
        )
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=4 * mm))


def _section(title: str):
    sec_style = ParagraphStyle(
        "rsec", fontName="Helvetica-Bold", fontSize=11,
        textColor=WHITE, leading=14
    )
    return [
        _ColorBar(W - 2 * MARGIN, 7 * mm, BLUE),
        Spacer(1, -7 * mm),
        Paragraph(f"  {title.upper()}", sec_style),
        Spacer(1, 4 * mm),
    ]


def _body(size=9):
    return ParagraphStyle(
        "rbody", fontName="Helvetica", fontSize=size,
        textColor=colors.HexColor("#333333"), leading=13
    )


def _bold(size=9):
    return ParagraphStyle(
        "rbold", fontName="Helvetica-Bold", fontSize=size,
        textColor=BLUE, leading=13
    )


def generate(candidate, output_path: str):
    logo_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "assets", "ldh_logo.jpg")
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
    )

    story = []
    _header(story, candidate, logo_path)

    # Summary
    story.extend(_section("Professional Summary"))
    story.append(Paragraph(candidate.summary or "", _body(9)))
    story.append(Spacer(1, 5 * mm))

    # Skills
    if candidate.skills:
        story.extend(_section("Core Skills"))
        usable = W - 2 * MARGIN
        chunks = [candidate.skills[i:i+3] for i in range(0, len(candidate.skills), 3)]
        for chunk in chunks:
            row = [Paragraph(f"• {s}", _body(9)) for s in chunk]
            while len(row) < 3:
                row.append(Paragraph("", _body(9)))
            t = Table([row], colWidths=[usable / 3] * 3)
            t.setStyle(TableStyle([
                ("LEFTPADDING",  (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(t)
        story.append(Spacer(1, 5 * mm))

    # Experience
    story.extend(_section("Professional Experience"))
    meta_style = ParagraphStyle(
        "emeta", fontName="Helvetica-Oblique", fontSize=8,
        textColor=MID_GRAY, leading=11
    )
    for exp in candidate.experience:
        story.append(Paragraph(exp.get("role", ""), _bold(10)))
        story.append(
            Paragraph(
                f"{exp.get('company','')}  |  {exp.get('period','')}",
                meta_style,
            )
        )
        if exp.get("description"):
            story.append(Paragraph(exp["description"], _body(8)))
        for ach in exp.get("achievements", []):
            story.append(Paragraph(f"▸  {ach}", _body(8)))
        story.append(Spacer(1, 4 * mm))

    # Education
    if candidate.education:
        story.extend(_section("Education"))
        for edu in candidate.education:
            story.append(Paragraph(edu.get("degree", ""), _bold(9)))
            inst = edu.get("institution", "") or ""
            year = edu.get("year", "") or ""
            if year.strip().lower() in ("", "none", "n/a", "unknown", "not specified"):
                year = ""
            edu_line = f"{inst}  —  {year}" if year else inst
            story.append(Paragraph(edu_line, _body(8)))
            story.append(Spacer(1, 3 * mm))

    # Certifications
    if candidate.certifications:
        story.extend(_section("Certifications"))
        for cert in candidate.certifications:
            story.append(Paragraph(f"• {cert}", _body(9)))
        story.append(Spacer(1, 3 * mm))

    # Languages
    if candidate.languages:
        story.extend(_section("Languages"))
        langs = "   |   ".join(
            f"{l.get('lang','')} ({l.get('level','')})" for l in candidate.languages
        )
        story.append(Paragraph(langs, _body(9)))

    # Footer
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    story.append(Paragraph(
        "This resume has been formatted and anonymized by LDH Latam Digital Hub by Stefanini — Confidential",
        ParagraphStyle("rfooter", fontName="Helvetica", fontSize=7,
                       textColor=MID_GRAY, alignment=TA_CENTER),
    ))

    doc.build(story)
    return output_path
