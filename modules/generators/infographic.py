"""
Talent Infographic — data-driven visual one-pager.

Fundamentally different from the Branded Resume:
  • Header: KPI stat boxes (years, skills count, certs, industries)
  • Sidebar: keyword skill tags + proficiency bar chart + language meters + rating score
  • Main: summary card + career timeline (connected dots) + industry tags + education
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
C_BLUE_LT   = colors.HexColor("#E4EEF8")
C_ORANGE    = colors.HexColor("#FF6B00")
C_ORANGE_LT = colors.HexColor("#FFF3EB")
C_SIDEBAR   = colors.HexColor("#F3F7FC")
C_WHITE     = colors.white
C_GRAY      = colors.HexColor("#555555")
C_GRAY_LT   = colors.HexColor("#DDDDDD")
C_DARK      = colors.HexColor("#1A1A2E")

PW, PH = A4   # 595.28 × 841.89 pt

# ── Layout constants ──────────────────────────────────────────────────────────
HEADER_H   = 76 * mm
FOOTER_H   = 12 * mm
SIDEBAR_W  = PW * 0.37        # ≈ 220 pt / 77 mm
MARGIN     = 5 * mm
BODY_Y_TOP = PH - HEADER_H
BODY_Y_BOT = FOOTER_H
BODY_H     = BODY_Y_TOP - BODY_Y_BOT
MAIN_X     = SIDEBAR_W

SB_M = MARGIN                  # sidebar left margin
SB_R = SIDEBAR_W - MARGIN      # sidebar right edge
SB_W = SB_R - SB_M            # sidebar usable width

MN_M = MAIN_X + MARGIN        # main content left
MN_R = PW - MARGIN             # main content right
MN_W = MN_R - MN_M            # main content width


# ── Drawing helpers ───────────────────────────────────────────────────────────
def _rrect(c, x, y, w, h, r=2 * mm, fill_color=None, stroke_color=None, lw=0.5):
    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(lw)
    p = c.beginPath()
    p.roundRect(x, y, w, h, r)
    c.drawPath(p, fill=1 if fill_color else 0, stroke=1 if stroke_color else 0)


def _para(c, text, x, y, w, h, font="Helvetica", size=8,
          color=C_DARK, align=TA_LEFT, leading=None):
    style = ParagraphStyle(
        "p", fontName=font, fontSize=size, textColor=color,
        alignment=align, leading=leading or size * 1.4,
        spaceAfter=0, spaceBefore=0,
    )
    p = Paragraph(text, style)
    p.wrapOn(c, w, h)
    p.drawOn(c, x, y - p.height)
    return p.height


def _section_sb(c, label, y):
    """Sidebar section header: orange accent bar + bold blue label."""
    c.setFillColor(C_ORANGE)
    c.rect(SB_M, y - 1 * mm, 2.5 * mm, 5 * mm, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(C_BLUE)
    c.drawString(SB_M + 4 * mm, y + 0.5 * mm, label.upper())
    return y - 7 * mm


def _section_mn(c, label, y):
    """Main area section: full-width blue band with white label."""
    band_h = 6.5 * mm
    c.setFillColor(C_BLUE)
    c.rect(MN_M, y - band_h, MN_W, band_h, fill=1, stroke=0)
    c.setFillColor(C_ORANGE)
    c.rect(MN_M, y - band_h, 2 * mm, band_h, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(MN_M + 5 * mm, y - band_h + 2 * mm, label.upper())
    return y - band_h - 3 * mm


def _parse_rating(rating_str):
    """'Senior / 8.5/10' → (8.5, 'Senior')"""
    m = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", rating_str or "")
    score = float(m.group(1)) if m else None
    seniority = (rating_str or "").split("/")[0].strip()
    return score, seniority


# ── HEADER ────────────────────────────────────────────────────────────────────
def _draw_header(c, candidate, logo_path):
    # Background
    c.setFillColor(C_BLUE_DARK)
    c.rect(0, PH - HEADER_H, PW, HEADER_H, fill=1, stroke=0)
    # Right-side lighter accent
    c.setFillColor(C_BLUE_MID)
    c.rect(PW * 0.55, PH - HEADER_H, PW * 0.45, HEADER_H, fill=1, stroke=0)
    # Orange left stripe
    c.setFillColor(C_ORANGE)
    c.rect(0, PH - HEADER_H, 3.5 * mm, HEADER_H, fill=1, stroke=0)

    # Logo — top right, aspect-correct
    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            logo_h = 12 * mm
            logo_w = min(logo_h * (iw / ih), 58 * mm)
            c.drawImage(
                img,
                PW - logo_w - 5 * mm, PH - logo_h - 4 * mm,
                width=logo_w, height=logo_h,
                preserveAspectRatio=True, mask="auto",
            )
        except Exception:
            pass

    name_x = 9 * mm

    # Candidate name
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(name_x, PH - 19 * mm, candidate.display_name)

    # Title
    c.setFillColor(C_ORANGE)
    c.setFont("Helvetica-BoldOblique", 11)
    c.drawString(name_x, PH - 28 * mm, candidate.title)

    # Location / work model
    meta_parts = []
    if candidate.current_location:
        meta_parts.append(candidate.current_location)
    if candidate.work_model:
        meta_parts.append(candidate.work_model)
    if meta_parts:
        c.setFillColor(C_GRAY_LT)
        c.setFont("Helvetica", 7.5)
        c.drawString(name_x, PH - 35.5 * mm, "  ·  ".join(meta_parts))

    # ── KPI stat boxes ─────────────────────────────────────────────────────
    kpis = []
    if candidate.years_of_experience:
        kpis.append((str(candidate.years_of_experience), "Years of Exp."))
    if candidate.skills:
        kpis.append((str(len(candidate.skills)), "Technical Skills"))
    if candidate.certifications:
        kpis.append((str(len(candidate.certifications)), "Certifications"))
    if candidate.key_industries:
        kpis.append((str(len(candidate.key_industries)), "Industries"))
    elif candidate.experience:
        kpis.append((str(len(candidate.experience)), "Companies"))

    n = min(len(kpis), 4)
    if n:
        box_h    = 21 * mm
        box_y    = PH - HEADER_H + 2.5 * mm   # anchored to bottom of header
        total_w  = PW - 14 * mm
        box_unit = total_w / n

        for i, (value, label) in enumerate(kpis[:4]):
            bx = 7 * mm + i * box_unit
            bw = box_unit - 3 * mm

            # Box background
            c.setFillColor(colors.HexColor("#0A2060"))
            c.rect(bx, box_y, bw, box_h, fill=1, stroke=0)
            # Orange top accent
            c.setFillColor(C_ORANGE)
            c.rect(bx, box_y + box_h - 1.5 * mm, bw, 1.5 * mm, fill=1, stroke=0)

            # Value (large number)
            c.setFillColor(C_ORANGE)
            c.setFont("Helvetica-Bold", 17)
            vw = c.stringWidth(value, "Helvetica-Bold", 17)
            c.drawString(bx + (bw - vw) / 2, box_y + 9.5 * mm, value)

            # Label (small text)
            c.setFillColor(C_GRAY_LT)
            c.setFont("Helvetica", 5.8)
            lw = c.stringWidth(label, "Helvetica", 5.8)
            c.drawString(bx + (bw - lw) / 2, box_y + 4 * mm, label)

    # Bottom orange line
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
    c.setLineWidth(0.4)
    c.line(SIDEBAR_W, FOOTER_H, SIDEBAR_W, BODY_Y_TOP)

    y = BODY_Y_TOP - 6 * mm

    # ── Core expertise ────────────────────────────────────────────────────────
    if candidate.core_expertise:
        y = _section_sb(c, "Core Expertise", y)
        h = _para(c, candidate.core_expertise, SB_M, y, SB_W, 28 * mm,
                  font="Helvetica-Oblique", size=7.5, color=C_DARK, leading=11)
        y -= (h + 5 * mm)

    # ── Skill keyword tags ────────────────────────────────────────────────────
    if candidate.skills:
        y = _section_sb(c, "Technical Keywords", y)
        tag_x = SB_M
        tag_y = y
        colors_cycle = [C_ORANGE, C_BLUE_MID, C_BLUE, C_ORANGE, C_BLUE_MID]

        for i, skill in enumerate(candidate.skills[:12]):
            tag_text = skill[:17]
            tw = c.stringWidth(tag_text, "Helvetica-Bold", 6.5) + 6 * mm
            if tag_x + tw > SB_R + 1 * mm:
                tag_x = SB_M
                tag_y -= 7.5 * mm
            if tag_y < FOOTER_H + 90 * mm:
                break

            bg = colors_cycle[i % len(colors_cycle)]
            _rrect(c, tag_x, tag_y - 5 * mm, tw, 5.8 * mm,
                   r=1.5 * mm, fill_color=bg)
            c.setFillColor(C_WHITE)
            c.setFont("Helvetica-Bold", 6.5)
            c.drawString(tag_x + 3 * mm, tag_y - 3 * mm, tag_text)
            tag_x += tw + 2 * mm

        y = tag_y - 10 * mm

    # ── Proficiency chart ─────────────────────────────────────────────────────
    if candidate.skills and y > FOOTER_H + 85 * mm:
        y = _section_sb(c, "Skill Proficiency", y)
        top_skills = candidate.skills[:6]
        # Simulated proficiency (descending from top skill)
        pcts = [1.0, 0.93, 0.86, 0.79, 0.72, 0.65]
        bar_max = SB_W - 10 * mm

        for i, (sk, pct) in enumerate(zip(top_skills, pcts)):
            if y < FOOTER_H + 45 * mm:
                break
            label_text = sk[:22]
            c.setFont("Helvetica", 6.5)
            c.setFillColor(C_DARK)
            c.drawString(SB_M, y, label_text)
            pct_label = f"{int(pct * 100)}%"
            c.setFont("Helvetica-Bold", 6)
            c.setFillColor(C_GRAY)
            c.drawRightString(SB_R, y + 0.2 * mm, pct_label)
            y -= 3.8 * mm

            # Background bar
            c.setFillColor(C_GRAY_LT)
            c.rect(SB_M, y, bar_max, 3 * mm, fill=1, stroke=0)
            # Filled bar — orange top 3, blue rest
            bar_col = C_ORANGE if i < 3 else C_BLUE_MID
            c.setFillColor(bar_col)
            c.rect(SB_M, y, bar_max * pct, 3 * mm, fill=1, stroke=0)
            y -= 5.5 * mm

        y -= 3 * mm

    # ── Languages ─────────────────────────────────────────────────────────────
    if candidate.languages and y > FOOTER_H + 42 * mm:
        y = _section_sb(c, "Languages", y)
        dot_map = {
            "native": 5, "fluent": 5, "advanced": 4,
            "upper-intermediate": 4, "intermediate": 3,
            "basic": 2, "beginner": 1, "elementary": 1,
        }
        for lang in candidate.languages[:4]:
            if y < FOOTER_H + 22 * mm:
                break
            name  = lang.get("lang", "")
            level = lang.get("level", "")
            filled = dot_map.get(level.lower(), 3)

            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(C_BLUE)
            c.drawString(SB_M, y, name)
            c.setFont("Helvetica", 6.5)
            c.setFillColor(C_GRAY)
            c.drawString(SB_M, y - 4 * mm, level)

            # Five filled/empty circles on the right
            cx_start = SB_R - 5 * 5.5 * mm
            for d in range(5):
                cx = cx_start + d * 5.5 * mm
                c.setFillColor(C_ORANGE if d < filled else C_GRAY_LT)
                c.circle(cx, y - 1.5 * mm, 2 * mm, fill=1, stroke=0)

            y -= 11 * mm

        y -= 2 * mm

    # ── Profile assessment ────────────────────────────────────────────────────
    if candidate.overall_rating and y > FOOTER_H + 30 * mm:
        y = _section_sb(c, "Profile Assessment", y)
        score, seniority = _parse_rating(candidate.overall_rating)

        if seniority:
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(C_BLUE)
            c.drawString(SB_M, y, seniority)
            y -= 5 * mm

        if score is not None:
            bar_max = SB_W - 2 * mm
            # Background
            c.setFillColor(C_GRAY_LT)
            c.rect(SB_M, y, bar_max, 4.5 * mm, fill=1, stroke=0)
            # Filled bar — color by score
            bar_col = C_ORANGE if score >= 8 else C_BLUE_MID if score >= 6 else C_GRAY
            c.setFillColor(bar_col)
            c.rect(SB_M, y, bar_max * (score / 10), 4.5 * mm, fill=1, stroke=0)
            # Score label inside bar
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(C_WHITE)
            score_label = f"{score}/10"
            c.drawString(SB_M + 2 * mm, y + 1.3 * mm, score_label)
            y -= 8 * mm

        if candidate.key_strengths and y > FOOTER_H + 12 * mm:
            snippet = candidate.key_strengths[:160]
            if len(candidate.key_strengths) > 160:
                snippet += "…"
            h = _para(c, snippet, SB_M, y, SB_W, 22 * mm,
                      font="Helvetica", size=6.5, color=C_GRAY, leading=9.5)
            y -= h


# ── MAIN CONTENT ──────────────────────────────────────────────────────────────
def _draw_main(c, candidate):
    y = BODY_Y_TOP - 5 * mm

    # ── Executive summary card ────────────────────────────────────────────────
    y = _section_mn(c, "Executive Summary", y)
    card_h = 36 * mm
    # Light blue card
    c.setFillColor(C_BLUE_LT)
    c.rect(MN_M, y - card_h, MN_W, card_h, fill=1, stroke=0)
    # Card border
    c.setStrokeColor(C_BLUE_MID)
    c.setLineWidth(0.5)
    c.rect(MN_M, y - card_h, MN_W, card_h, fill=0, stroke=1)
    # Orange left accent on card
    c.setFillColor(C_ORANGE)
    c.rect(MN_M, y - card_h, 2.5 * mm, card_h, fill=1, stroke=0)

    h = _para(c, candidate.summary, MN_M + 5 * mm, y - 3 * mm, MN_W - 8 * mm, 34 * mm,
              font="Helvetica", size=8, color=C_DARK, leading=12)
    y -= (max(h + 6 * mm, card_h) + 5 * mm)

    # ── Career timeline ───────────────────────────────────────────────────────
    y = _section_mn(c, "Career Timeline", y)

    tl_x    = MN_M + 4 * mm    # vertical line & dot x
    text_x  = tl_x + 8 * mm
    text_w  = MN_R - text_x

    for i, exp in enumerate(candidate.experience[:4]):
        if y < FOOTER_H + 48 * mm:
            break

        role         = exp.get("role", "")
        company      = exp.get("company", "")
        period       = exp.get("period", "")
        achievements = exp.get("achievements", [])

        # Timeline dot
        dot_col = C_ORANGE if i == 0 else C_BLUE_MID
        c.setFillColor(dot_col)
        c.circle(tl_x, y - 1.5 * mm, 3 * mm, fill=1, stroke=0)
        if i == 0:
            # Hollow centre for current role
            c.setFillColor(C_WHITE)
            c.circle(tl_x, y - 1.5 * mm, 1.3 * mm, fill=1, stroke=0)

        # Role — bold blue
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColor(C_BLUE)
        c.drawString(text_x, y, role[:52])

        # Period — right aligned, orange
        c.setFont("Helvetica", 7)
        c.setFillColor(C_ORANGE)
        c.drawRightString(MN_R, y, period)
        y -= 4.5 * mm

        # Company — italic gray
        c.setFont("Helvetica-Oblique", 7.5)
        c.setFillColor(C_GRAY)
        c.drawString(text_x, y, company[:58])
        y -= 4.5 * mm

        # Achievements (max 2)
        for ach in achievements[:2]:
            if y < FOOTER_H + 38 * mm:
                break
            bullet = f"<font color='#FF6B00'>▸</font>  {ach}"
            h = _para(c, bullet, text_x, y, text_w, 14 * mm,
                      font="Helvetica", size=7, color=C_DARK, leading=10.5)
            y -= (h + 1.5 * mm)

        # Connector line to next entry
        if i < len(candidate.experience) - 1 and y > FOOTER_H + 43 * mm:
            c.setStrokeColor(C_GRAY_LT)
            c.setLineWidth(1.5)
            c.line(tl_x, y - 2 * mm, tl_x, y - 7 * mm)

        y -= 7 * mm

    # ── Industries / domain tags ──────────────────────────────────────────────
    if candidate.key_industries and y > FOOTER_H + 22 * mm:
        y -= 1 * mm
        y = _section_mn(c, "Industries & Domain", y)
        tag_x = MN_M
        for ind in candidate.key_industries[:6]:
            label = ind[:22]
            tw = c.stringWidth(label, "Helvetica", 7) + 5.5 * mm
            if tag_x + tw > MN_R - 1 * mm:
                break
            _rrect(c, tag_x, y - 5.5 * mm, tw, 6.5 * mm,
                   r=1.5 * mm, fill_color=C_BLUE_LT, stroke_color=C_BLUE_MID, lw=0.5)
            c.setFillColor(C_BLUE)
            c.setFont("Helvetica", 7)
            c.drawString(tag_x + 2.5 * mm, y - 3 * mm, label)
            tag_x += tw + 3 * mm
        y -= 12 * mm

    # ── Education ─────────────────────────────────────────────────────────────
    if candidate.education and y > FOOTER_H + 18 * mm:
        y = _section_mn(c, "Education", y)
        for edu in candidate.education[:2]:
            if y < FOOTER_H + 12 * mm:
                break
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(C_BLUE)
            c.drawString(MN_M, y, edu.get("degree", "")[:55])
            c.setFont("Helvetica", 7.5)
            c.setFillColor(C_GRAY)
            meta = f"{edu.get('institution', '')}  ·  {edu.get('year', '')}".strip(" ·")
            c.drawString(MN_M, y - 4 * mm, meta[:60])
            y -= 12 * mm

    # ── Technical highlights (if space) ──────────────────────────────────────
    if candidate.technical_highlights and y > FOOTER_H + 16 * mm:
        c.setFillColor(C_ORANGE_LT)
        hl_h = 12 * mm
        c.rect(MN_M, y - hl_h, MN_W, hl_h, fill=1, stroke=0)
        c.setFillColor(C_ORANGE)
        c.rect(MN_M, y - hl_h, 2.5 * mm, hl_h, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(C_BLUE)
        c.drawString(MN_M + 5 * mm, y - 3.5 * mm, "KEY ACHIEVEMENT")
        snippet = candidate.technical_highlights[:100]
        _para(c, snippet, MN_M + 5 * mm, y - 6.5 * mm, MN_W - 8 * mm, 8 * mm,
              font="Helvetica", size=7, color=C_DARK, leading=10)


# ── FOOTER ────────────────────────────────────────────────────────────────────
def _draw_footer(c):
    c.setFillColor(C_BLUE_DARK)
    c.rect(0, 0, PW, FOOTER_H, fill=1, stroke=0)
    c.setFillColor(C_ORANGE)
    c.rect(0, FOOTER_H - 1 * mm, PW, 1 * mm, fill=1, stroke=0)
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica", 6.5)
    c.drawString(5 * mm, 4.5 * mm,
                 "LDH Latam Digital Hub by Stefanini  —  Confidential")
    c.setFillColor(C_GRAY_LT)
    c.setFont("Helvetica", 6)
    c.drawRightString(PW - 5 * mm, 4.5 * mm,
                      "This document is prepared exclusively for client evaluation purposes.")


# ── PUBLIC ENTRY POINT ────────────────────────────────────────────────────────
def generate(candidate, output_path: str) -> str:
    logo_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "assets", "ldh_logo.jpg")
    )

    cv = canvas.Canvas(output_path, pagesize=A4)
    cv.setTitle(f"Talent Infographic — {candidate.display_name}")
    cv.setAuthor("LDH Latam Digital Hub by Stefanini")

    _draw_header(cv, candidate, logo_path)
    _draw_sidebar(cv, candidate)
    _draw_main(cv, candidate)
    _draw_footer(cv)

    cv.save()
    return output_path
