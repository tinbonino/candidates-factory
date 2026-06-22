"""
Talent Infographic — LDH one-pager, reference-aligned layout.

A4 portrait:
  ┌─────────────────────────────────────────────┐  HEADER 65mm (white)
  │ [LDH logo]  Name · Title · Summary          │
  ├──────────────┬──────────────────────────────┤  BODY ~170mm
  │ LEFT  (37%)  │  RIGHT (63%)                 │
  │ ▌ PROF.PROF. │  ▌ STRATEGIC VALUE           │
  │  30+  yrs    │  Qualitative blocks (3-4)    │
  │  Badge 1     │  Language profile            │
  │  Badge 2     │                              │
  │  Badge 3     │                              │
  │  Certs       │                              │
  ├──────────────┴──────────────────────────────┤  TECH 52mm
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
C_WHITE     = colors.white
C_GRAY      = colors.HexColor("#666666")
C_GRAY_LT   = colors.HexColor("#DDDDDD")
C_GRAY_BG   = colors.HexColor("#F4F7FC")
C_DARK      = colors.HexColor("#222222")
C_TECH_BG   = colors.HexColor("#EEF3FA")

PW, PH = A4   # 595.28 × 841.89 pt

# ── Layout ────────────────────────────────────────────────────────────────────
HEADER_H  = 65 * mm
FOOTER_H  = 12 * mm
TECH_H    = 52 * mm
SIDEBAR_W = PW * 0.37   # ≈ 220 pt

BODY_TOP = PH - HEADER_H
BODY_BOT = FOOTER_H + TECH_H
BODY_H   = BODY_TOP - BODY_BOT   # ≈ 482 pt / 170 mm

M = 6 * mm

SB_X = M
SB_R = SIDEBAR_W - M
SB_W = SB_R - SB_X

MN_X = SIDEBAR_W + M
MN_R = PW - M
MN_W = MN_R - MN_X


# ── Helpers ───────────────────────────────────────────────────────────────────
def _para(c, text, x, y, w, h, font="Helvetica", size=9,
          color=C_DARK, align=TA_LEFT, leading=None):
    style = ParagraphStyle(
        "p", fontName=font, fontSize=size, textColor=color,
        alignment=align, leading=leading or size * 1.45,
        spaceAfter=0, spaceBefore=0,
    )
    p = Paragraph(text, style)
    p.wrapOn(c, w, h)
    p.drawOn(c, x, y - p.height)
    return p.height


def _col_header(c, x, y, w, label):
    """Dark blue full-width column header band."""
    box_h = 13 * mm
    c.setFillColor(C_BLUE_DARK)
    c.rect(x, y - box_h, w, box_h, fill=1, stroke=0)
    c.setFillColor(C_ORANGE)
    c.rect(x, y - box_h, 4 * mm, box_h, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(x + 7 * mm, y - box_h + 4 * mm, label.upper())
    return y - box_h - 4 * mm


def _block_title(c, x, y, label, width=None):
    """Bold block title with orange underline accent.
    Auto-reduces font if title is too wide for the column."""
    col_w = width or SB_W
    label_up = label.upper()

    # Pick font size that fits within column width
    font_size = 9.5
    for fs in (9.5, 8.5, 8.0, 7.5):
        if c.stringWidth(label_up, "Helvetica-Bold", fs) <= col_w:
            font_size = fs
            break

    c.setFont("Helvetica-Bold", font_size)
    c.setFillColor(C_BLUE)
    c.drawString(x, y, label_up)
    c.setStrokeColor(C_ORANGE)
    c.setLineWidth(1.5)
    title_w = min(c.stringWidth(label_up, "Helvetica-Bold", font_size), col_w)
    c.line(x, y - 2 * mm, x + title_w, y - 2 * mm)
    return y - 7 * mm


def _divider(c, x, y, w):
    """Thin horizontal separator."""
    c.setStrokeColor(C_GRAY_LT)
    c.setLineWidth(0.4)
    c.line(x, y, x + w, y)
    return y - 4 * mm


def _gradient_bar(c, x, y, w, h, pct):
    """Horizontal blue→orange gradient bar, filled to pct ∈ [0,1]."""
    filled = w * min(max(pct, 0.0), 1.0)
    steps  = 40
    sw     = filled / steps if steps else 0
    r0, g0, b0 = 0/255,   48/255, 135/255   # #003087
    r1, g1, b1 = 255/255, 107/255, 0/255    # #FF6B00
    for i in range(steps):
        t = i / max(steps - 1, 1)
        c.setFillColorRGB(r0 + (r1-r0)*t, g0 + (g1-g0)*t, b0 + (b1-b0)*t)
        c.rect(x + i * sw, y, sw + 0.5, h, fill=1, stroke=0)
    if pct < 1.0:
        c.setFillColor(C_GRAY_LT)
        c.rect(x + filled, y, w - filled, h, fill=1, stroke=0)


def _parse_rating(s):
    m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", s or "")
    score = float(m.group(1)) if m else None
    seniority = (s or "").split("/")[0].strip()
    return score, seniority


# ── HEADER (white) ────────────────────────────────────────────────────────────
def _draw_header(c, candidate, logo_path):
    c.setFillColor(C_WHITE)
    c.rect(0, PH - HEADER_H, PW, HEADER_H, fill=1, stroke=0)

    # Left blue stripe
    c.setFillColor(C_BLUE)
    c.rect(0, PH - HEADER_H, 4 * mm, HEADER_H, fill=1, stroke=0)
    # Bottom orange rule
    c.setFillColor(C_ORANGE)
    c.rect(0, PH - HEADER_H, PW, 1.5 * mm, fill=1, stroke=0)

    text_x = 5 * mm + M

    # Logo
    logo_bottom = PH - 5 * mm
    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            logo_h = 13 * mm
            logo_w = min(logo_h * (iw / ih), 58 * mm)
            logo_bottom = PH - logo_h - 5 * mm
            c.drawImage(img, text_x, logo_bottom,
                        width=logo_w, height=logo_h,
                        preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    name_y = logo_bottom - 5 * mm

    # Name
    c.setFont("Helvetica-Bold", 21)
    c.setFillColor(C_BLUE)
    c.drawString(text_x, name_y, candidate.display_name)

    # Title
    c.setFont("Helvetica-BoldOblique", 11)
    c.setFillColor(C_ORANGE)
    c.drawString(text_x, name_y - 8 * mm, candidate.title or "")

    # Summary
    summary_y = name_y - 16 * mm
    avail_w = PW - text_x - M
    summary_h = _para(c, (candidate.summary or "")[:500], text_x, summary_y,
                      avail_w, 20 * mm, font="Helvetica", size=8,
                      color=C_GRAY, leading=11.5)

    # Meta info strip (location · work model · salary)
    meta_parts = []
    if candidate.current_location:
        meta_parts.append(candidate.current_location)
    if candidate.work_model:
        meta_parts.append(candidate.work_model)
    if candidate.salary_expectation:
        meta_parts.append(candidate.salary_expectation)
    if meta_parts:
        meta_y = summary_y - summary_h - 4 * mm
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#999999"))
        c.drawString(text_x, meta_y, "  ·  ".join(meta_parts))


# ── LEFT COLUMN ───────────────────────────────────────────────────────────────
def _draw_left(c, candidate):
    c.setFillColor(C_GRAY_BG)
    c.rect(0, BODY_BOT, SIDEBAR_W, BODY_H, fill=1, stroke=0)
    c.setStrokeColor(C_GRAY_LT)
    c.setLineWidth(0.4)
    c.line(SIDEBAR_W, BODY_BOT, SIDEBAR_W, BODY_TOP)

    y = BODY_TOP
    y = _col_header(c, 0, y, SIDEBAR_W, "Professional Excellence & Tech Match")

    # ── Years of experience ───────────────────────────────────────────────────
    if candidate.years_of_experience:
        # Subtle highlight box
        box_h = 28 * mm
        c.setFillColor(C_BLUE_LT)
        c.rect(SB_X - 1*mm, y - box_h, SB_W + 2*mm, box_h, fill=1, stroke=0)
        c.setFillColor(C_ORANGE)
        c.rect(SB_X - 1*mm, y - box_h, 3*mm, box_h, fill=1, stroke=0)

        num = f"{candidate.years_of_experience}+"
        c.setFont("Helvetica-Bold", 44)
        c.setFillColor(C_BLUE)
        nw = c.stringWidth(num, "Helvetica-Bold", 44)
        c.drawString(SB_X + (SB_W - nw) / 2, y - 9 * mm, num)

        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(C_BLUE)
        lbl = "YEARS OF EXPERIENCE"
        lw = c.stringWidth(lbl, "Helvetica-Bold", 8)
        c.drawString(SB_X + (SB_W - lw) / 2, y - box_h + 6 * mm, lbl)

        if candidate.availability:
            c.setFont("Helvetica", 7)
            c.setFillColor(C_GRAY)
            note = f"Available: {candidate.availability}"
            nw2 = c.stringWidth(note, "Helvetica", 7)
            c.drawString(SB_X + (SB_W - nw2) / 2, y - box_h + 2 * mm, note)

        y -= box_h + 5 * mm
        y = _divider(c, SB_X, y, SB_W)

    # ── Professional badges (AI-generated) ────────────────────────────────────
    badges = list(candidate.professional_badges or [])
    if not badges:
        if candidate.core_expertise:
            badges.append({"title": "Core Expertise", "body": candidate.core_expertise})
        if candidate.technical_highlights:
            badges.append({"title": "Key Achievement", "body": candidate.technical_highlights})

    for badge in badges[:3]:
        if y < BODY_BOT + 14 * mm:
            break
        title = badge.get("title", "")
        body  = badge.get("body", "")
        y = _block_title(c, SB_X, y, title)
        h = _para(c, body, SB_X, y, SB_W, 35 * mm,
                  font="Helvetica", size=8.5, color=C_DARK, leading=12.5)
        y -= (h + 3 * mm)
        y = _divider(c, SB_X, y, SB_W)

    # ── Certifications (fills remaining space) ────────────────────────────────
    if candidate.certifications and y > BODY_BOT + 12 * mm:
        y = _block_title(c, SB_X, y, "Certifications")
        for cert in candidate.certifications[:4]:
            if y < BODY_BOT + 6 * mm:
                break
            c.setFillColor(C_ORANGE)
            c.circle(SB_X + 2 * mm, y + 1 * mm, 1.8 * mm, fill=1, stroke=0)
            h = _para(c, cert, SB_X + 5.5 * mm, y + 3 * mm,
                      SB_W - 5.5 * mm, 10 * mm, font="Helvetica", size=8, color=C_DARK)
            y -= max(h, 5 * mm) + 1 * mm
        y -= 2 * mm

    # ── Overall rating bar ────────────────────────────────────────────────────
    if candidate.overall_rating and y > BODY_BOT + 14 * mm:
        y = _divider(c, SB_X, y, SB_W)
        score, seniority = _parse_rating(candidate.overall_rating)
        if seniority:
            c.setFont("Helvetica-Bold", 8.5)
            c.setFillColor(C_BLUE)
            c.drawString(SB_X, y, seniority)
            y -= 6 * mm
        if score is not None:
            bar_w = SB_W
            _gradient_bar(c, SB_X, y - 5 * mm, bar_w, 5 * mm, score / 10)
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(C_WHITE)
            c.drawString(SB_X + 2 * mm, y - 3.8 * mm, f"{score}/10")


# ── RIGHT COLUMN ──────────────────────────────────────────────────────────────
def _draw_right(c, candidate):
    c.setFillColor(C_WHITE)
    c.rect(SIDEBAR_W, BODY_BOT, PW - SIDEBAR_W, BODY_H, fill=1, stroke=0)

    y = BODY_TOP
    y = _col_header(c, SIDEBAR_W, y, PW - SIDEBAR_W, "Strategic Value & Leadership")

    dot_map = {"native": 5, "fluent": 5, "advanced": 4,
               "upper-intermediate": 4, "intermediate": 3,
               "basic": 2, "beginner": 1, "elementary": 1}

    # ── Qualitative profile blocks (AI-generated) ─────────────────────────────
    qual = list(candidate.qualitative_profile or [])

    # Fallback from structured fields
    if not qual:
        if candidate.key_industries:
            ind_list = ", ".join(candidate.key_industries[:4])
            qual.append({
                "title": "Multi-Industry Versatility",
                "body": f"Demonstrated high-impact delivery across {ind_list} sectors, adapting technical solutions to diverse business contexts and regulatory environments.",
            })
        if len(candidate.languages or []) > 1:
            langs = " and ".join(l.get("lang", "") for l in candidate.languages[:3])
            qual.append({
                "title": "Bilingual Technical Communicator",
                "body": f"Professional proficiency in {langs}, enabling seamless collaboration with global and regional teams across time zones.",
            })
        if candidate.key_strengths:
            qual.append({"title": "Leadership & Team Development",
                         "body": candidate.key_strengths})

    # Reserve space for language section: title (7mm) + N langs (9mm each)
    n_langs = len(candidate.languages or [])
    lang_reserve = (7 + n_langs * 9) * mm if n_langs else 0

    for block in qual[:3]:
        if y < BODY_BOT + lang_reserve + 14 * mm:
            break
        title = block.get("title", "")
        body  = block.get("body", "")
        y = _block_title(c, MN_X, y, title, width=MN_W)
        h = _para(c, body, MN_X, y, MN_W, 35 * mm,
                  font="Helvetica", size=9, color=C_DARK, leading=13.5)
        y -= (h + 4 * mm)
        y = _divider(c, MN_X, y, MN_W)

    # ── Language profile ──────────────────────────────────────────────────────
    if candidate.languages and y > BODY_BOT + 18 * mm:
        y = _block_title(c, MN_X, y, "Language Profile", width=MN_W)
        for lang in candidate.languages[:4]:
            if y < BODY_BOT + 8 * mm:
                break
            name   = lang.get("lang", "")
            level  = lang.get("level", "")
            filled = dot_map.get(level.lower(), 3)

            c.setFont("Helvetica-Bold", 8.5)
            c.setFillColor(C_DARK)
            c.drawString(MN_X, y, name)

            c.setFont("Helvetica", 8)
            c.setFillColor(C_GRAY)
            c.drawString(MN_X + 30 * mm, y, level)

            dot_r   = 2.5 * mm
            dot_gap = 6 * mm
            dot_x0  = MN_R - 5 * dot_gap
            for d in range(5):
                c.setFillColor(C_ORANGE if d < filled else C_GRAY_LT)
                c.circle(dot_x0 + d * dot_gap, y + 1.2 * mm, dot_r, fill=1, stroke=0)

            y -= 9 * mm


# ── TECH SECTION (full width bottom) ─────────────────────────────────────────
def _draw_tech_section(c, candidate):
    y_top = FOOTER_H + TECH_H
    y_bot = FOOTER_H

    c.setFillColor(C_TECH_BG)
    c.rect(0, y_bot, PW, TECH_H, fill=1, stroke=0)
    c.setFillColor(C_ORANGE)
    c.rect(0, y_top - 1.5 * mm, PW, 1.5 * mm, fill=1, stroke=0)

    # Section title
    title_y = y_top - 7 * mm
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(C_BLUE)
    title = "TECHNICAL FOCUS & READINESS"
    tw = c.stringWidth(title, "Helvetica-Bold", 10)
    c.drawString((PW - tw) / 2, title_y, title)

    # Column layout
    hdr_y     = title_y - 6 * mm
    col_x     = M
    col_w_sk  = PW * 0.22
    col_w_bar = PW * 0.38
    col_x_bar = col_x + col_w_sk + 3 * mm
    col_x_det = col_x_bar + col_w_bar + 5 * mm
    col_w_det = PW - col_x_det - M

    # Column headers
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(C_BLUE)
    c.drawString(col_x, hdr_y, "TECHNICAL FOCUS")
    c.drawString(col_x_bar, hdr_y, "CAPABILITY LEVEL")
    c.drawString(col_x_det, hdr_y, "DETAIL / TOOLS")
    c.setStrokeColor(C_BLUE_MID)
    c.setLineWidth(0.6)
    c.line(M, hdr_y - 2.5 * mm, PW - M, hdr_y - 2.5 * mm)

    # Skill rows — 5 skills max so bar height << row height (no overlap)
    skills = candidate.skills[:5]
    pcts   = [0.95, 0.88, 0.80, 0.73, 0.65]

    int_items = []
    if candidate.integration_skills:
        int_items = [s.strip() for s in re.split(r"[,;]", candidate.integration_skills)]

    rows_area = hdr_y - 2.5 * mm - y_bot - 3 * mm
    n         = max(len(skills), 1)
    row_h     = rows_area / n   # each row bucket height (pt)
    bar_h     = min(row_h * 0.55, 5 * mm)  # bar ≤ 55% of row & max 5mm

    # Draw alternating backgrounds first (behind everything)
    for i in range(n):
        if i % 2 == 0:
            ry_top = hdr_y - 2.5 * mm - i * row_h
            c.setFillColor(colors.HexColor("#E2EAF5"))
            c.rect(0, ry_top - row_h, PW, row_h, fill=1, stroke=0)

    # Draw content rows
    for i, (skill, pct) in enumerate(zip(skills, pcts)):
        ry_top = hdr_y - 2.5 * mm - i * row_h        # top of this row bucket
        ry_mid = ry_top - row_h / 2                   # vertical centre of row

        # Skill name (vertically centred)
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(C_DARK)
        # Shrink font until it fits the column width
        sk_label = skill
        sk_size  = 8.5
        for fs in (8.5, 8.0, 7.5, 7.0):
            if c.stringWidth(sk_label, "Helvetica-Bold", fs) <= col_w_sk - 2 * mm:
                sk_size = fs
                break
        else:
            # Still too long — truncate with ellipsis
            while c.stringWidth(sk_label + "…", "Helvetica-Bold", 7.0) > col_w_sk - 2 * mm and len(sk_label) > 1:
                sk_label = sk_label[:-1]
            sk_label += "…"
        c.setFont("Helvetica-Bold", sk_size)
        c.drawString(col_x, ry_mid - 1.5 * mm, sk_label)

        # Gradient bar (centred vertically in row)
        bar_y = ry_mid - bar_h / 2
        _gradient_bar(c, col_x_bar, bar_y, col_w_bar, bar_h, pct)

        # Detail text (vertically centred)
        if i < len(int_items) and int_items[i]:
            det = int_items[i][:42]
        else:
            det = f"{int(pct * 100)}%"
        c.setFont("Helvetica", 8)
        c.setFillColor(C_GRAY)
        c.drawString(col_x_det, ry_mid - 1.5 * mm, det)

        # Row separator at bottom of bucket
        c.setStrokeColor(C_GRAY_LT)
        c.setLineWidth(0.3)
        c.line(M, ry_top - row_h, PW - M, ry_top - row_h)


# ── FOOTER ────────────────────────────────────────────────────────────────────
def _draw_footer(c):
    c.setFillColor(C_BLUE_DARK)
    c.rect(0, 0, PW, FOOTER_H, fill=1, stroke=0)
    c.setFillColor(C_ORANGE)
    c.rect(0, FOOTER_H - 1 * mm, PW, 1 * mm, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica", 7)
    c.drawString(M, 4.5 * mm, "LDH Latam Digital Hub by Stefanini  —  Confidential")
    c.setFillColor(C_GRAY_LT)
    c.setFont("Helvetica", 6.5)
    c.drawRightString(PW - M, 4.5 * mm,
                      "Prepared exclusively for client evaluation purposes.")


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
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
