"""
Talent Infographic — LDH one-pager, reference-aligned layout.

A4 portrait:
  ┌─────────────────────────────────────────────┐  HEADER 65mm (white)
  │ [LDH logo]  Name · Title · Summary          │
  ├──────────────┬──────────────────────────────┤  BODY ~170mm
  │ LEFT  (37%)  │  RIGHT (63%)                 │
  │ ▌ PROF.PROF. │  ▌ STRATEGIC VALUE           │
  │  30+  yrs    │  Career highlights           │
  │  Core expert │  Industry tags               │
  │  Key achieve │  Languages                   │
  │  Certs       │  Assessment                  │
  ├──────────────┴──────────────────────────────┤  TECH 50mm
  │  TECHNICAL FOCUS & READINESS                 │
  │  Skill  [══════════════░░░]  detail text     │
  └─────────────────────────────────────────────┘  FOOTER 12mm
"""
import os
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# ── Palette ───────────────────────────────────────────────────────────────────
C_BLUE      = colors.HexColor("#003087")
C_BLUE_DARK = colors.HexColor("#001D52")
C_BLUE_MID  = colors.HexColor("#1A5CB0")
C_BLUE_LT   = colors.HexColor("#E8F0FA")
C_ORANGE    = colors.HexColor("#FF6B00")
C_ORANGE_LT = colors.HexColor("#FFF0E5")
C_WHITE     = colors.white
C_GRAY      = colors.HexColor("#555555")
C_GRAY_LT   = colors.HexColor("#DDDDDD")
C_GRAY_BG   = colors.HexColor("#F4F7FC")
C_DARK      = colors.HexColor("#1A1A2E")
C_TECH_BG   = colors.HexColor("#EEF3FA")

PW, PH = A4   # 595.28 × 841.89 pt

# ── Layout ────────────────────────────────────────────────────────────────────
HEADER_H  = 65 * mm    # 184 pt  — white header
FOOTER_H  = 12 * mm    # 34 pt   — dark footer
TECH_H    = 50 * mm    # 142 pt  — full-width tech section
SIDEBAR_W = PW * 0.37  # ≈ 220 pt

BODY_TOP = PH - HEADER_H          # top of left/right columns
BODY_BOT = FOOTER_H + TECH_H      # bottom of left/right columns
BODY_H   = BODY_TOP - BODY_BOT    # ≈ 482 pt / 170 mm

M = 6 * mm   # general margin

# sidebar shortcuts
SB_X = M
SB_R = SIDEBAR_W - M
SB_W = SB_R - SB_X

# main content shortcuts
MN_X = SIDEBAR_W + M
MN_R = PW - M
MN_W = MN_R - MN_X


# ── Helpers ───────────────────────────────────────────────────────────────────
def _para(c, text, x, y, w, h, font="Helvetica", size=8,
          color=C_DARK, align=TA_LEFT, leading=None):
    """Draw a Paragraph and return the height it consumed."""
    style = ParagraphStyle(
        "p", fontName=font, fontSize=size, textColor=color,
        alignment=align, leading=leading or size * 1.4,
        spaceAfter=0, spaceBefore=0,
    )
    p = Paragraph(text, style)
    p.wrapOn(c, w, h)
    p.drawOn(c, x, y - p.height)
    return p.height


def _col_header(c, x, y, w, label):
    """Dark blue column-header box, returns y below it."""
    box_h = 11 * mm
    c.setFillColor(C_BLUE_DARK)
    c.rect(x, y - box_h, w, box_h, fill=1, stroke=0)
    # Orange left accent
    c.setFillColor(C_ORANGE)
    c.rect(x, y - box_h, 3 * mm, box_h, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 5 * mm, y - box_h + 3.5 * mm, label.upper())
    return y - box_h - 3 * mm


def _block_title(c, x, y, label):
    """Bold section block title (inside a column)."""
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(C_BLUE)
    c.drawString(x, y, label.upper())
    return y - 5 * mm


def _divider(c, x, y, w):
    """Thin horizontal rule."""
    c.setStrokeColor(C_GRAY_LT)
    c.setLineWidth(0.4)
    c.line(x, y, x + w, y)
    return y - 3 * mm


def _gradient_bar(c, x, y, w, h, pct):
    """Horizontal gradient bar (blue → orange) filled to pct ∈ [0,1]."""
    filled = w * min(max(pct, 0.0), 1.0)
    steps  = 40
    sw     = filled / steps if steps else 0
    r0, g0, b0 = 0/255, 48/255, 135/255   # #003087
    r1, g1, b1 = 255/255, 107/255, 0/255  # #FF6B00
    for i in range(steps):
        t = i / max(steps - 1, 1)
        c.setFillColorRGB(r0 + (r1-r0)*t, g0 + (g1-g0)*t, b0 + (b1-b0)*t)
        c.rect(x + i * sw, y, sw + 0.5, h, fill=1, stroke=0)
    # Empty portion
    if pct < 1.0:
        c.setFillColor(C_GRAY_LT)
        c.rect(x + filled, y, w - filled, h, fill=1, stroke=0)


def _parse_rating(s):
    """'Senior / 8.5/10' → (8.5, 'Senior')"""
    m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", s or "")
    score = float(m.group(1)) if m else None
    seniority = (s or "").split("/")[0].strip()
    return score, seniority


# ── HEADER (white) ────────────────────────────────────────────────────────────
def _draw_header(c, candidate, logo_path):
    # White background
    c.setFillColor(C_WHITE)
    c.rect(0, PH - HEADER_H, PW, HEADER_H, fill=1, stroke=0)

    # Orange bottom border
    c.setFillColor(C_ORANGE)
    c.rect(0, PH - HEADER_H, PW, 1.5 * mm, fill=1, stroke=0)
    # Blue accent on left edge
    c.setFillColor(C_BLUE)
    c.rect(0, PH - HEADER_H, 3.5 * mm, HEADER_H, fill=1, stroke=0)

    text_x = 4 * mm + M

    # Logo (if available)
    logo_h = 0
    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            logo_display_h = 14 * mm
            logo_display_w = min(logo_display_h * (iw / ih), 60 * mm)
            c.drawImage(
                img,
                text_x, PH - logo_display_h - 5 * mm,
                width=logo_display_w, height=logo_display_h,
                preserveAspectRatio=True, mask="auto",
            )
            logo_h = logo_display_h + 5 * mm
        except Exception:
            pass

    name_y = PH - logo_h - 10 * mm

    # Candidate name
    c.setFont("Helvetica-Bold", 20)
    c.setFillColor(C_BLUE)
    c.drawString(text_x, name_y, candidate.display_name)

    # Title
    c.setFont("Helvetica-BoldOblique", 11)
    c.setFillColor(C_ORANGE)
    c.drawString(text_x, name_y - 8 * mm, candidate.title)

    # Summary (short — 2 lines max)
    avail_w = PW - text_x - M
    _para(c, candidate.summary[:300], text_x, name_y - 16 * mm,
          avail_w, 22 * mm, font="Helvetica", size=7.5, color=C_GRAY, leading=11)


# ── LEFT COLUMN ───────────────────────────────────────────────────────────────
def _draw_left(c, candidate):
    # Gray background
    c.setFillColor(C_GRAY_BG)
    c.rect(0, BODY_BOT, SIDEBAR_W, BODY_H, fill=1, stroke=0)
    # Right border
    c.setStrokeColor(C_GRAY_LT)
    c.setLineWidth(0.4)
    c.line(SIDEBAR_W, BODY_BOT, SIDEBAR_W, BODY_TOP)

    y = BODY_TOP

    # Column header
    y = _col_header(c, 0, y, SIDEBAR_W, "Professional Profile")

    # ── BIG years number ─────────────────────────────────────────────────────
    if candidate.years_of_experience:
        num = str(candidate.years_of_experience) + "+"
        c.setFont("Helvetica-Bold", 46)
        c.setFillColor(C_ORANGE)
        nw = c.stringWidth(num, "Helvetica-Bold", 46)
        c.drawString(SB_X + (SB_W - nw) / 2, y - 8 * mm, num)
        y -= 19 * mm
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(C_BLUE)
        label = "YEARS OF EXPERIENCE"
        lw = c.stringWidth(label, "Helvetica-Bold", 8)
        c.drawString(SB_X + (SB_W - lw) / 2, y, label)
        y -= 4 * mm
        # Availability sub-note
        if candidate.availability:
            c.setFont("Helvetica", 6.5)
            c.setFillColor(C_GRAY)
            note = f"Available: {candidate.availability}"
            nw = c.stringWidth(note, "Helvetica", 6.5)
            c.drawString(SB_X + (SB_W - nw) / 2, y, note)
            y -= 4 * mm
        y -= 3 * mm
        y = _divider(c, SB_X, y, SB_W)

    # ── Core Expertise block ──────────────────────────────────────────────────
    if candidate.core_expertise and y > BODY_BOT + 45 * mm:
        y = _block_title(c, SB_X, y, "Core Expertise")
        h = _para(c, candidate.core_expertise,
                  SB_X, y, SB_W, 28 * mm,
                  font="Helvetica-Oblique", size=7.5, color=C_DARK, leading=11)
        y -= (h + 4 * mm)
        y = _divider(c, SB_X, y, SB_W)

    # ── Key Achievement block ─────────────────────────────────────────────────
    if candidate.technical_highlights and y > BODY_BOT + 32 * mm:
        y = _block_title(c, SB_X, y, "Key Achievement")
        h = _para(c, candidate.technical_highlights,
                  SB_X, y, SB_W, 22 * mm,
                  font="Helvetica", size=7.5, color=C_DARK, leading=11)
        y -= (h + 4 * mm)
        y = _divider(c, SB_X, y, SB_W)

    # ── Certifications block ──────────────────────────────────────────────────
    if candidate.certifications and y > BODY_BOT + 18 * mm:
        y = _block_title(c, SB_X, y, "Certifications")
        for cert in candidate.certifications[:4]:
            if y < BODY_BOT + 8 * mm:
                break
            c.setFillColor(C_ORANGE)
            c.circle(SB_X + 1.5 * mm, y + 1 * mm, 1.5 * mm, fill=1, stroke=0)
            c.setFont("Helvetica", 6.5)
            c.setFillColor(C_DARK)
            c.drawString(SB_X + 4.5 * mm, y, cert[:32])
            y -= 5 * mm

    # ── Overall rating (bottom of left column) ────────────────────────────────
    if candidate.overall_rating and y > BODY_BOT + 14 * mm:
        y = _divider(c, SB_X, y - 2 * mm, SB_W)
        score, seniority = _parse_rating(candidate.overall_rating)
        if seniority:
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(C_BLUE)
            c.drawString(SB_X, y, seniority)
            y -= 5 * mm
        if score is not None:
            bar_w = SB_W - 2 * mm
            _gradient_bar(c, SB_X, y - 4 * mm, bar_w, 4 * mm, score / 10)
            c.setFont("Helvetica-Bold", 6.5)
            c.setFillColor(C_WHITE)
            c.drawString(SB_X + 2 * mm, y - 3 * mm, f"{score}/10")


# ── RIGHT COLUMN ──────────────────────────────────────────────────────────────
def _draw_right(c, candidate):
    # White background
    c.setFillColor(C_WHITE)
    c.rect(SIDEBAR_W, BODY_BOT, PW - SIDEBAR_W, BODY_H, fill=1, stroke=0)

    y = BODY_TOP

    # Column header
    y = _col_header(c, SIDEBAR_W, y, PW - SIDEBAR_W, "Strategic Value & Leadership")

    # ── Career Highlights ─────────────────────────────────────────────────────
    y = _block_title(c, MN_X, y, "Career Highlights")

    dot_map = {"native": 5, "fluent": 5, "advanced": 4,
               "upper-intermediate": 4, "intermediate": 3,
               "basic": 2, "beginner": 1, "elementary": 1}

    for exp in candidate.experience[:3]:
        if y < BODY_BOT + 95 * mm:
            break
        role    = exp.get("role", "")
        company = exp.get("company", "")
        period  = exp.get("period", "")
        achs    = exp.get("achievements", [])

        # Role + period
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(C_BLUE)
        c.drawString(MN_X, y, role[:52])
        c.setFont("Helvetica", 7)
        c.setFillColor(C_ORANGE)
        pw = c.stringWidth(period, "Helvetica", 7)
        c.drawString(MN_R - pw, y, period)
        y -= 4.5 * mm

        # Company
        c.setFont("Helvetica-Oblique", 7.5)
        c.setFillColor(C_GRAY)
        c.drawString(MN_X, y, company[:58])
        y -= 4.5 * mm

        # Top achievement
        for ach in achs[:1]:
            bullet = f"<font color='#FF6B00'>▸</font>  {ach}"
            h = _para(c, bullet, MN_X + 1*mm, y, MN_W - 1*mm, 12*mm,
                      font="Helvetica", size=7.5, color=C_DARK, leading=11)
            y -= (h + 2 * mm)

        y -= 2 * mm

    y = _divider(c, MN_X, y, MN_W)

    # ── Multi-Industry Versatility ────────────────────────────────────────────
    if candidate.key_industries and y > BODY_BOT + 40 * mm:
        y = _block_title(c, MN_X, y, "Multi-Industry Versatility")
        tag_x = MN_X
        for ind in candidate.key_industries[:6]:
            label = ind[:22]
            tw = c.stringWidth(label, "Helvetica", 7) + 6 * mm
            if tag_x + tw > MN_R - 1 * mm:
                tag_x = MN_X
                y -= 7.5 * mm
            if y < BODY_BOT + 30 * mm:
                break
            # Blue outline tag
            c.setFillColor(C_BLUE_LT)
            c.setStrokeColor(C_BLUE_MID)
            c.setLineWidth(0.5)
            p = c.beginPath()
            p.roundRect(tag_x, y - 5 * mm, tw, 6 * mm, 1.5 * mm)
            c.drawPath(p, fill=1, stroke=1)
            c.setFont("Helvetica", 7)
            c.setFillColor(C_BLUE)
            c.drawString(tag_x + 3 * mm, y - 2.8 * mm, label)
            tag_x += tw + 3 * mm
        y -= 10 * mm
        y = _divider(c, MN_X, y, MN_W)

    # ── Languages ─────────────────────────────────────────────────────────────
    if candidate.languages and y > BODY_BOT + 30 * mm:
        y = _block_title(c, MN_X, y, "Bilingual / Multilingual Profile")
        for lang in candidate.languages[:4]:
            if y < BODY_BOT + 12 * mm:
                break
            name  = lang.get("lang", "")
            level = lang.get("level", "")
            filled = dot_map.get(level.lower(), 3)

            c.setFont("Helvetica-Bold", 7.5)
            c.setFillColor(C_DARK)
            c.drawString(MN_X, y, name)
            c.setFont("Helvetica", 7)
            c.setFillColor(C_GRAY)
            c.drawString(MN_X + 25 * mm, y, level)

            # Dot indicators (right side)
            dot_start = MN_R - 5 * 5 * mm
            for d in range(5):
                cx = dot_start + d * 5 * mm
                c.setFillColor(C_ORANGE if d < filled else C_GRAY_LT)
                c.circle(cx, y + 1 * mm, 2 * mm, fill=1, stroke=0)

            y -= 7 * mm


# ── TECH SECTION (full width bottom) ─────────────────────────────────────────
def _draw_tech_section(c, candidate):
    y_top = FOOTER_H + TECH_H
    y_bot = FOOTER_H

    # Background
    c.setFillColor(C_TECH_BG)
    c.rect(0, y_bot, PW, TECH_H, fill=1, stroke=0)
    # Top border
    c.setFillColor(C_ORANGE)
    c.rect(0, y_top - 1.5 * mm, PW, 1.5 * mm, fill=1, stroke=0)

    # Title row (centered)
    title_y = y_top - 7 * mm
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(C_BLUE)
    title = "TECHNICAL FOCUS & READINESS"
    tw = c.stringWidth(title, "Helvetica-Bold", 9)
    c.drawString((PW - tw) / 2, title_y, title)

    # Column header line
    hdr_y = title_y - 5 * mm
    col_x     = M
    col_w_sk  = PW * 0.22    # skill name column
    col_w_bar = PW * 0.38    # gradient bar column
    col_x_bar = col_x + col_w_sk + 3 * mm
    col_x_det = col_x_bar + col_w_bar + 4 * mm
    col_w_det = PW - col_x_det - M

    c.setFont("Helvetica-Bold", 6.5)
    c.setFillColor(C_BLUE)
    c.drawString(col_x, hdr_y, "TECHNICAL FOCUS")
    c.drawString(col_x_bar, hdr_y, "CAPABILITY LEVEL")
    c.drawString(col_x_det, hdr_y, "DETAIL / TOOLS")
    c.setStrokeColor(C_GRAY_LT)
    c.setLineWidth(0.5)
    c.line(M, hdr_y - 2 * mm, PW - M, hdr_y - 2 * mm)

    # Skill rows
    skills = candidate.skills[:6]
    pcts   = [0.95, 0.88, 0.82, 0.76, 0.69, 0.62]

    # Split integration_skills for the details column
    int_items = []
    if candidate.integration_skills:
        int_items = [s.strip() for s in re.split(r"[,;]", candidate.integration_skills)]

    rows_area = hdr_y - 2 * mm - y_bot - 2 * mm
    row_h = rows_area / max(len(skills), 1)

    for i, (skill, pct) in enumerate(zip(skills, pcts)):
        ry = hdr_y - 2 * mm - (i + 0.5) * row_h

        # Alternating row bg
        if i % 2 == 0:
            c.setFillColor(colors.HexColor("#E3EAF6"))
            c.rect(0, ry - row_h * 0.5, PW, row_h, fill=1, stroke=0)

        # Skill name
        c.setFont("Helvetica", 8)
        c.setFillColor(C_DARK)
        c.drawString(col_x, ry - 1.5 * mm, skill[:26])

        # Gradient bar
        bar_h = 4.5 * mm
        _gradient_bar(c, col_x_bar, ry - bar_h - 0.5 * mm, col_w_bar, bar_h, pct)

        # Detail text
        if i < len(int_items) and int_items[i]:
            det = int_items[i][:40]
        else:
            det = f"{int(pct * 100)}% proficiency"
        c.setFont("Helvetica", 7)
        c.setFillColor(C_GRAY)
        c.drawString(col_x_det, ry - 1.5 * mm, det)

        # Row divider
        c.setStrokeColor(C_GRAY_LT)
        c.setLineWidth(0.3)
        c.line(M, ry - row_h * 0.5, PW - M, ry - row_h * 0.5)


# ── FOOTER ────────────────────────────────────────────────────────────────────
def _draw_footer(c):
    c.setFillColor(C_BLUE_DARK)
    c.rect(0, 0, PW, FOOTER_H, fill=1, stroke=0)
    c.setFillColor(C_ORANGE)
    c.rect(0, FOOTER_H - 1 * mm, PW, 1 * mm, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica", 6.5)
    c.drawString(M, 4.5 * mm, "LDH Latam Digital Hub by Stefanini  —  Confidential")
    c.setFillColor(C_GRAY_LT)
    c.setFont("Helvetica", 6)
    c.drawRightString(PW - M, 4.5 * mm,
                      "Prepared exclusively for client evaluation purposes.")


# ── PUBLIC ENTRY POINT ────────────────────────────────────────────────────────
def generate(candidate, output_path: str) -> str:
    logo_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "assets", "ldh_logo.jpg")
    )

    cv = canvas.Canvas(output_path, pagesize=A4)
    cv.setTitle(f"Talent Infographic — {candidate.display_name}")
    cv.setAuthor("LDH Latam Digital Hub by Stefanini")

    _draw_header(cv, candidate, logo_path)
    _draw_left(cv, candidate)
    _draw_right(cv, candidate)
    _draw_tech_section(cv, candidate)
    _draw_footer(cv)

    cv.save()
    return output_path
