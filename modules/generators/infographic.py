"""
Talent Card — corporate infographic PDF for presenting candidates to enterprise clients.
Uses ReportLab canvas directly for pixel-precise layout control.

Layout (A4 portrait):
  ┌──────────────────────────────────────────┐
  │  HEADER — dark blue, name + title + KPIs │
  ├───────────┬──────────────────────────────┤
  │  SIDEBAR  │  MAIN CONTENT                │
  │  (35%)    │  Summary                     │
  │  Skills   │  Experience                  │
  │  Languages│  Education                   │
  │  Certs    │                              │
  ├───────────┴──────────────────────────────┤
  │  FOOTER — LDH branding                   │
  └──────────────────────────────────────────┘
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# ── Palette ──────────────────────────────────────────────────────────────────
C_BLUE      = colors.HexColor("#003087")
C_BLUE_DARK = colors.HexColor("#001D52")
C_BLUE_MID  = colors.HexColor("#004BB5")
C_ORANGE    = colors.HexColor("#FF6B00")
C_ORANGE_LT = colors.HexColor("#FF8C33")
C_SIDEBAR   = colors.HexColor("#F0F4FA")
C_WHITE     = colors.white
C_GRAY      = colors.HexColor("#666666")
C_GRAY_LT   = colors.HexColor("#CCCCCC")
C_DARK      = colors.HexColor("#1A1A2E")

PW, PH = A4   # 595.28 x 841.89 pt

# ── Layout constants ─────────────────────────────────────────────────────────
HEADER_H    = 52 * mm
FOOTER_H    = 12 * mm
SIDEBAR_W   = 64 * mm
MARGIN      = 5 * mm
BODY_Y_TOP  = PH - HEADER_H
BODY_Y_BOT  = FOOTER_H
BODY_H      = BODY_Y_TOP - BODY_Y_BOT
MAIN_X      = SIDEBAR_W
MAIN_W      = PW - SIDEBAR_W


# ── Helper: draw rounded rect ─────────────────────────────────────────────────
def _rrect(c, x, y, w, h, r=2*mm, fill=1, stroke=0):
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    c.drawPath(p, fill=fill, stroke=stroke)


# ── Helper: clipped text via Paragraph ───────────────────────────────────────
def _para(c, text, x, y, w, h, font="Helvetica", size=8,
          color=C_DARK, align=TA_LEFT, leading=None):
    style = ParagraphStyle(
        "p", fontName=font, fontSize=size,
        textColor=color, alignment=align,
        leading=leading or size * 1.35,
        spaceAfter=0, spaceBefore=0,
    )
    p = Paragraph(text, style)
    p.wrapOn(c, w, h)
    p.drawOn(c, x, y - p.height)
    return p.height


# ── Section title (sidebar) ───────────────────────────────────────────────────
def _sidebar_section(c, label, y):
    c.setFillColor(C_ORANGE)
    c.rect(MARGIN, y - 0.8*mm, 3*mm, 4*mm, fill=1, stroke=0)
    c.setFillColor(C_BLUE)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(MARGIN + 4.5*mm, y, label.upper())
    return y - 6.5*mm


# ── Section title (main area) ────────────────────────────────────────────────
def _main_section(c, label, y):
    c.setFillColor(C_BLUE)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(MAIN_X + MARGIN, y, label.upper())
    c.setStrokeColor(C_ORANGE)
    c.setLineWidth(0.8)
    c.line(MAIN_X + MARGIN, y - 1.5*mm, PW - MARGIN, y - 1.5*mm)
    return y - 6*mm


# ── HEADER ────────────────────────────────────────────────────────────────────
def _draw_header(c, candidate, logo_path):
    # Background gradient effect — two overlapping rects
    c.setFillColor(C_BLUE_DARK)
    c.rect(0, PH - HEADER_H, PW, HEADER_H, fill=1, stroke=0)
    c.setFillColor(C_BLUE_MID)
    c.rect(PW * 0.55, PH - HEADER_H, PW * 0.45, HEADER_H, fill=1, stroke=0)

    # Orange accent stripe on left
    c.setFillColor(C_ORANGE)
    c.rect(0, PH - HEADER_H, 3*mm, HEADER_H, fill=1, stroke=0)

    # Logo top-right
    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            c.drawImage(img, PW - 52*mm, PH - 14*mm,
                        width=48*mm, height=10*mm,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Name
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(8*mm, PH - 18*mm, candidate.display_name)

    # Title
    c.setFillColor(C_ORANGE_LT)
    c.setFont("Helvetica-BoldOblique", 11)
    c.drawString(8*mm, PH - 26*mm, candidate.title)

    # KPI pills
    kpis = []
    if candidate.years_of_experience:
        kpis.append(f"{candidate.years_of_experience} yrs exp.")
    if candidate.availability:
        kpis.append(candidate.availability)
    if candidate.work_model:
        kpis.append(candidate.work_model)

    pill_x = 8*mm
    pill_y = PH - 36*mm
    for kpi in kpis[:4]:
        text_w = c.stringWidth(kpi, "Helvetica-Bold", 7.5) + 6*mm
        _rrect(c, pill_x, pill_y - 0.5*mm, text_w, 5.5*mm,
               r=2*mm, fill=1, stroke=0)
        c.setFillColor(C_WHITE)
        c.rect(pill_x, pill_y - 0.5*mm, text_w, 5.5*mm, fill=1, stroke=0)
        c.setFillColor(C_BLUE_DARK)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(pill_x + 3*mm, pill_y + 1*mm, kpi)
        pill_x += text_w + 2.5*mm

    # Bottom divider
    c.setStrokeColor(C_ORANGE)
    c.setLineWidth(1.5)
    c.line(0, PH - HEADER_H, PW, PH - HEADER_H)


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
def _draw_sidebar(c, candidate):
    # Background
    c.setFillColor(C_SIDEBAR)
    c.rect(0, FOOTER_H, SIDEBAR_W, BODY_H, fill=1, stroke=0)

    # Right border
    c.setStrokeColor(C_GRAY_LT)
    c.setLineWidth(0.3)
    c.line(SIDEBAR_W, FOOTER_H, SIDEBAR_W, BODY_Y_TOP)

    y = BODY_Y_TOP - 8*mm

    # ── Skills ────────────────────────────────────────────────────────────────
    y = _sidebar_section(c, "Core Skills", y)
    skills = candidate.skills[:10]
    bar_max_w = SIDEBAR_W - 2*MARGIN - 2*mm
    for i, skill in enumerate(skills):
        fill_pct = max(0.45, 1.0 - i * 0.055)
        # Label
        c.setFillColor(C_DARK)
        c.setFont("Helvetica", 7)
        skill_label = skill[:26]
        c.drawString(MARGIN, y, skill_label)
        y -= 4*mm
        # Bar background
        c.setFillColor(C_GRAY_LT)
        c.rect(MARGIN, y, bar_max_w, 2.2*mm, fill=1, stroke=0)
        # Filled bar
        c.setFillColor(C_ORANGE if i < 3 else C_BLUE_MID)
        c.rect(MARGIN, y, bar_max_w * fill_pct, 2.2*mm, fill=1, stroke=0)
        y -= 4.5*mm
        if y < FOOTER_H + 70*mm:
            break

    y -= 3*mm

    # ── Languages ─────────────────────────────────────────────────────────────
    if candidate.languages and y > FOOTER_H + 45*mm:
        y = _sidebar_section(c, "Languages", y)
        for lang in candidate.languages[:5]:
            name = lang.get("lang", "")
            level = lang.get("level", "")
            c.setFont("Helvetica-Bold", 7.5)
            c.setFillColor(C_BLUE)
            c.drawString(MARGIN, y, name)
            c.setFont("Helvetica", 7)
            c.setFillColor(C_GRAY)
            level_x = MARGIN + c.stringWidth(name, "Helvetica-Bold", 7.5) + 2*mm
            c.drawString(level_x, y, level)
            # Dots indicator
            dot_levels = {"native": 5, "fluent": 5, "advanced": 4,
                          "upper-intermediate": 4, "intermediate": 3,
                          "basic": 2, "beginner": 1, "elementary": 1}
            dots = dot_levels.get(level.lower(), 3)
            for d in range(5):
                c.setFillColor(C_ORANGE if d < dots else C_GRAY_LT)
                c.circle(SIDEBAR_W - MARGIN - (4-d)*4*mm,
                         y + 1.5*mm, 1.5*mm, fill=1, stroke=0)
            y -= 6*mm

        y -= 2*mm

    # ── Certifications ────────────────────────────────────────────────────────
    if candidate.certifications and y > FOOTER_H + 20*mm:
        y = _sidebar_section(c, "Certifications", y)
        for cert in candidate.certifications[:6]:
            c.setFillColor(C_ORANGE)
            c.circle(MARGIN + 1.5*mm, y + 1.5*mm, 1.5*mm, fill=1, stroke=0)
            c.setFont("Helvetica", 6.5)
            c.setFillColor(C_DARK)
            # Wrap long cert names
            max_chars = 28
            cert_text = cert[:max_chars] + ("…" if len(cert) > max_chars else "")
            c.drawString(MARGIN + 4*mm, y, cert_text)
            y -= 5*mm
            if y < FOOTER_H + 8*mm:
                break

    # ── Industries ────────────────────────────────────────────────────────────
    if hasattr(candidate, 'key_industries') and candidate.key_industries and y > FOOTER_H + 15*mm:
        y -= 2*mm
        y = _sidebar_section(c, "Industries", y)
        for ind in candidate.key_industries[:4]:
            c.setFont("Helvetica", 7)
            c.setFillColor(C_DARK)
            c.drawString(MARGIN + 2*mm, y, f"· {ind[:26]}")
            y -= 5*mm


# ── MAIN CONTENT ──────────────────────────────────────────────────────────────
def _draw_main(c, candidate):
    x0 = MAIN_X + MARGIN
    right = PW - MARGIN
    w = right - x0
    y = BODY_Y_TOP - 7*mm

    # ── Summary ────────────────────────────────────────────────────────────────
    y = _main_section(c, "Executive Summary", y)
    h = _para(c, candidate.summary, x0, y, w, 30*mm,
               font="Helvetica", size=8, color=C_DARK, leading=11.5)
    y -= (h + 5*mm)

    # ── Experience ────────────────────────────────────────────────────────────
    y = _main_section(c, "Professional Experience", y)

    for exp in candidate.experience:
        if y < FOOTER_H + 35*mm:
            break

        role   = exp.get("role", "")
        company = exp.get("company", "")
        period  = exp.get("period", "")
        desc    = exp.get("description", "")
        achievements = exp.get("achievements", [])

        # Role — bold blue
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(C_BLUE)
        c.drawString(x0, y, role[:65])

        # Period — right-aligned orange
        c.setFont("Helvetica", 7.5)
        c.setFillColor(C_ORANGE)
        period_w = c.stringWidth(period, "Helvetica", 7.5)
        c.drawString(right - period_w, y, period)
        y -= 4.5*mm

        # Company
        c.setFont("Helvetica-Oblique", 7.5)
        c.setFillColor(C_GRAY)
        c.drawString(x0, y, company[:70])
        y -= 4*mm

        # Description
        if desc:
            h = _para(c, desc, x0, y, w, 20*mm,
                       font="Helvetica", size=7.5, color=C_DARK, leading=11)
            y -= (h + 2*mm)

        # Achievements
        for ach in achievements[:3]:
            if y < FOOTER_H + 20*mm:
                break
            bullet = f"<font color='#FF6B00'>▸</font>  {ach}"
            h = _para(c, bullet, x0 + 2*mm, y, w - 2*mm, 15*mm,
                       font="Helvetica", size=7.5, color=C_DARK, leading=11)
            y -= (h + 1*mm)

        # Separator
        c.setStrokeColor(C_GRAY_LT)
        c.setLineWidth(0.3)
        c.line(x0, y - 2*mm, right, y - 2*mm)
        y -= 6*mm

    # ── Education ────────────────────────────────────────────────────────────
    if candidate.education and y > FOOTER_H + 20*mm:
        y = _main_section(c, "Education", y)
        for edu in candidate.education[:3]:
            if y < FOOTER_H + 14*mm:
                break
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(C_BLUE)
            c.drawString(x0, y, edu.get("degree", "")[:60])
            c.setFont("Helvetica", 7.5)
            c.setFillColor(C_GRAY)
            meta = f"{edu.get('institution','')}  ·  {edu.get('year','')}".strip(" ·")
            c.drawString(x0, y - 4*mm, meta[:65])
            y -= 11*mm


# ── FOOTER ────────────────────────────────────────────────────────────────────
def _draw_footer(c, logo_path):
    c.setFillColor(C_BLUE_DARK)
    c.rect(0, 0, PW, FOOTER_H, fill=1, stroke=0)

    c.setFillColor(C_ORANGE)
    c.rect(0, FOOTER_H - 1*mm, PW, 1*mm, fill=1, stroke=0)

    c.setFillColor(C_WHITE)
    c.setFont("Helvetica", 6.5)
    c.drawString(5*mm, 4.5*mm, "LDH Latam Digital Hub by Stefanini  —  Confidential")

    c.setFillColor(C_GRAY_LT)
    c.setFont("Helvetica", 6)
    notice = "This document is prepared exclusively for client evaluation purposes."
    c.drawRightString(PW - 5*mm, 4.5*mm, notice)


# ── PUBLIC ENTRY POINT ────────────────────────────────────────────────────────
def generate(candidate, output_path: str) -> str:
    logo_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "assets", "ldh_logo.jpg")
    )

    cv = canvas.Canvas(output_path, pagesize=A4)
    cv.setTitle(f"Talent Card — {candidate.display_name}")
    cv.setAuthor("LDH Latam Digital Hub by Stefanini")

    _draw_header(cv, candidate, logo_path)
    _draw_sidebar(cv, candidate)
    _draw_main(cv, candidate)
    _draw_footer(cv, logo_path)

    cv.save()
    return output_path
