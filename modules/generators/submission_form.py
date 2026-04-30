"""
Generates the Candidate Submission Form PDF.
Structure mirrors CANDIDATE SUBMISSION FORM 2.docx exactly.
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from templates.submission_fields import SUBMISSION_SECTIONS

BLUE = colors.HexColor("#003087")
ORANGE = colors.HexColor("#FF6B00")
LIGHT_GRAY = colors.HexColor("#F2F2F2")
MID_GRAY = colors.HexColor("#AAAAAA")
DARK = colors.HexColor("#333333")

W, H = A4
MARGIN = 18 * mm
USABLE = W - 2 * MARGIN
LABEL_W = 52 * mm
VALUE_W = USABLE - LABEL_W


def _logo_header(story, logo_path):
    if logo_path and os.path.exists(logo_path):
        from reportlab.platypus import Image
        story.append(Image(logo_path, width=50 * mm, height=18 * mm))
        story.append(Spacer(1, 3 * mm))

    story.append(Paragraph(
        "CANDIDATE SUBMISSION FORM",
        ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=16,
                       textColor=BLUE, alignment=TA_CENTER)
    ))
    story.append(Paragraph(
        "LDH Latam Digital Hub by Stefanini — Confidential",
        ParagraphStyle("sub", fontName="Helvetica", fontSize=9,
                       textColor=MID_GRAY, alignment=TA_CENTER, spaceBefore=2 * mm)
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=ORANGE,
                             spaceBefore=4 * mm, spaceAfter=5 * mm))


def _section_header(title: str):
    return [
        Paragraph(
            title,
            ParagraphStyle("sec", fontName="Helvetica-Bold", fontSize=10,
                           textColor=colors.white, leading=14)
        )
    ]


def _section_band(title: str) -> Table:
    t = Table(
        [_section_header(title)],
        colWidths=[USABLE],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
    ]))
    return t


def _field_row(label: str, value: str) -> Table:
    label_style = ParagraphStyle(
        "fl", fontName="Helvetica-Bold", fontSize=8.5, textColor=BLUE
    )
    value_style = ParagraphStyle(
        "fv", fontName="Helvetica", fontSize=8.5, textColor=DARK, leading=12
    )
    border = {"style": "LINEBELOW", "color": colors.HexColor("#DDDDDD")}
    t = Table(
        [[Paragraph(label, label_style), Paragraph(value or "—", value_style)]],
        colWidths=[LABEL_W, VALUE_W],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), LIGHT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
    ]))
    return t


def _resolve(candidate, key: str) -> str:
    # property or attribute
    val = getattr(candidate, key, None)
    if val is None:
        return "—"
    if isinstance(val, list):
        if not val:
            return "—"
        if isinstance(val[0], dict):
            if "institution" in val[0]:
                return "\n".join(
                    f"{e.get('degree','')} — {e.get('institution','')} ({e.get('year','')})"
                    for e in val
                )
            if "lang" in val[0]:
                return "  |  ".join(
                    f"{l.get('lang','')} ({l.get('level','')})" for l in val
                )
        return "  •  ".join(str(v) for v in val)
    return str(val) if val else "—"


def generate(candidate, output_path: str):
    logo_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "assets", "ldh_logo.png")
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    story = []
    _logo_header(story, logo_path)

    for section in SUBMISSION_SECTIONS:
        rows = [_section_band(section["title"])]

        if section["fields"]:
            for f in section["fields"]:
                rows.append(_field_row(f["label"], _resolve(candidate, f["key"])))
        else:
            # Section 5: Professional Experience — rendered as sub-rows
            for exp in candidate.experience:
                role_label = f"{exp.get('role','')}\n{exp.get('company','')}  |  {exp.get('period','')}"
                desc_parts = []
                if exp.get("description"):
                    desc_parts.append(exp["description"])
                for ach in exp.get("achievements", []):
                    desc_parts.append(f"• {ach}")
                rows.append(_field_row(role_label, "\n".join(desc_parts)))

        story.append(KeepTogether(rows))
        story.append(Spacer(1, 3 * mm))

    # Footer
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceBefore=4 * mm))
    story.append(Paragraph(
        "LDH Latam Digital Hub by Stefanini — Confidential",
        ParagraphStyle("foot", fontName="Helvetica", fontSize=7,
                       textColor=MID_GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)
    return output_path
