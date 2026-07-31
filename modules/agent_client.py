"""
AgentClient — extracts structured candidate data from CV text.
Provider chain: Gemini (primary) → SAI → Groq (fallback).
"""
import json
import os
from dataclasses import dataclass, field
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an expert HR analyst working for LDH Latam Digital Hub by Stefanini. Your task is to analyze one or more documents about a candidate and return a single, valid JSON object with structured data AND a qualitative profile analysis. You never explain, comment, or add any text outside the JSON.

The input may contain:
- A RESUME / CV section (always present, primary source of structured data)
- One or more SUPPLEMENTARY DOCUMENT sections (e.g. technical tests, assessments) — use these to enrich technical_highlights, key_strengths, areas_for_growth, overall_rating, technical_accuracy, and the qualitative analysis. Do not extract personal or contact data from supplementary documents.

OUTPUT RULES:
- Return ONLY a raw JSON object — no markdown, no code fences, no explanation
- All text fields must be in English (translate if the CV is in another language)
- Never include contact information: no emails, phone numbers, LinkedIn URLs, or physical addresses
- If a field is not found in the CV, infer it where possible or return null
- NEVER use placeholder text such as "Not provided", "N/A", "Unknown", "Not specified" — always return null for missing fields

ANONYMIZATION:
- last_name_initial must be the first letter of last_name followed by a period (e.g. "Martinez" → "M.")
- Never include the full last name in the summary or any other field
- If the candidate's name is represented only as initials (e.g. "GT", "A.B.", "J.R."), set first_name to the full initials string (e.g. "GT"), last_name to the same initials string, and last_name_initial to "" (empty string)

REQUIRED JSON SCHEMA:
{
  "first_name": "string",
  "last_name": "string",
  "last_name_initial": "string",
  "title": "string — current or most recent professional role",
  "summary": "string — 3 to 5 sentence executive summary written in third person, synthesized from the full CV. Do NOT state a specific total number of years of experience (avoid phrases like '5+ years of experience', 'over 10 years', 'a decade of'). Describe seniority and scope qualitatively instead (e.g. 'seasoned', 'experienced across fintech and logistics'). Any years figure is handled separately from the dated work history.",
  "skills": ["string — list of 8 to 12 top technical and soft skills"],
  "core_expertise": "string — 1 to 2 sentence description of the candidate's main technical domain",
  "key_industries": ["string — industries the candidate has worked in"],
  "technical_highlights": "string — most notable technical achievement or technology stack",
  "integration_skills": "string — APIs, platforms, or integration technologies used",
  "key_training": ["string — relevant non-official courses or training programs"],
  "key_strengths": "string — 3 to 5 professional strengths as a short paragraph",
  "areas_for_growth": "string — honest and constructive development areas based on the CV",
  "overall_rating": "string — seniority level and score out of 10, e.g. 'Senior / 8.5/10'",
  "technical_accuracy": "string — brief assessment of the candidate's technical depth",
  "languages": [{"lang": "string", "level": "string"}],
  "experience": [
    {
      "company": "string",
      "role": "string",
      "period": "string",
      "description": "string — full description of responsibilities copied faithfully from the CV, preserving ALL details without summarizing or omitting anything",
      "achievements": ["string — include ALL bullet points, achievements, and responsibilities listed in the CV for this role, do not skip any"]
    }
  ],
  "education": [{"institution": "string", "degree": "string", "year": "string"}],
  "certifications": ["string"],
  "years_of_experience": "number — calculate by subtracting the earliest work experience start date from today's date (or the most recent end date). Sum overlapping roles only once. Always round DOWN to the nearest whole number. Example: Jan 2020 to Jun 2026 = 6 years.",
  "availability": "string or null",
  "salary_expectation": "string or null",
  "current_location": "string or null",
  "work_model": "string or null — Remote, Hybrid, or On-site",
  "visa_status": "string or null",
  "interview_availability": "string or null",
  "recruiter_comments": null,

  "professional_badges": [
    {
      "title": "string — 3 to 5 word bold specialty title (e.g. 'S/4HANA Implementation Specialist', 'Cloud Architecture Expert')",
      "body": "string — 2 to 3 sentences of specific evidence from the CV supporting this specialization, written in third person"
    }
  ],
  "qualitative_profile": [
    {
      "title": "string — 3 to 5 word strategic value or leadership quality title (e.g. 'Global Project Leadership', 'Multi-Industry Versatility', 'Bilingual Technical Communicator')",
      "body": "string — 2 to 3 sentences of qualitative analysis of this strength based on the CV, written in third person"
    }
  ]
}

QUALITATIVE ANALYSIS RULES:
- professional_badges: generate 2 to 3 items. Each badge must reflect a concrete technical specialization clearly evidenced in the CV (e.g. years in a specific technology, a notable project, a certification). Use specific data points.
- qualitative_profile: generate 3 to 4 items covering dimensions such as: leadership style, industry versatility, communication / language skills, innovation capacity, teamwork or mentoring ability, problem-solving approach. Each item must be grounded in specific evidence from the CV, not generic praise.
- Both arrays must be substantive and differentiated — avoid repeating the same idea across items."""


@dataclass
class CandidateData:
    first_name: str
    last_name: str
    last_name_initial: str
    title: str
    summary: str
    skills: list[str] = field(default_factory=list)
    core_expertise: str = ""
    key_industries: list[str] = field(default_factory=list)
    technical_highlights: str = ""
    integration_skills: str = ""
    key_training: list[str] = field(default_factory=list)
    key_strengths: str = ""
    areas_for_growth: str = ""
    overall_rating: str = ""
    technical_accuracy: str = ""
    current_location: Optional[str] = None
    work_model: Optional[str] = None
    visa_status: Optional[str] = None
    interview_availability: Optional[str] = None
    recruiter_comments: Optional[str] = None
    languages: list[dict] = field(default_factory=list)
    experience: list[dict] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    years_of_experience: int = 0
    availability: Optional[str] = None
    salary_expectation: Optional[str] = None
    professional_badges: list[dict] = field(default_factory=list)
    qualitative_profile: list[dict] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        name    = self.first_name or ""
        initial = self.last_name_initial or ""
        if name and initial:
            return f"{name} {initial}"
        return name or initial or "Candidate"

    def _lang_level(self, lang_name: str) -> str:
        for l in self.languages:
            if l.get("lang", "").lower() == lang_name.lower():
                return l.get("level", "")
        return ""

    @property
    def lang_english(self) -> str:
        return self._lang_level("English")

    @property
    def lang_portuguese(self) -> str:
        return self._lang_level("Portuguese")

    @property
    def lang_spanish(self) -> str:
        return self._lang_level("Spanish")

    @classmethod
    def from_dict(cls, data: dict) -> "CandidateData":
        return cls(
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            last_name_initial=data.get("last_name_initial", ""),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            skills=data.get("skills", []),
            core_expertise=data.get("core_expertise", ""),
            key_industries=data.get("key_industries", []),
            technical_highlights=data.get("technical_highlights", ""),
            integration_skills=data.get("integration_skills", ""),
            key_training=data.get("key_training", []),
            key_strengths=data.get("key_strengths", ""),
            areas_for_growth=data.get("areas_for_growth", ""),
            overall_rating=data.get("overall_rating", ""),
            technical_accuracy=data.get("technical_accuracy", ""),
            current_location=data.get("current_location"),
            work_model=data.get("work_model"),
            visa_status=data.get("visa_status"),
            interview_availability=data.get("interview_availability"),
            recruiter_comments=data.get("recruiter_comments"),
            languages=data.get("languages", []),
            experience=data.get("experience", []),
            education=data.get("education", []),
            certifications=data.get("certifications", []),
            years_of_experience=int(data.get("years_of_experience") or 0),
            availability=data.get("availability"),
            salary_expectation=data.get("salary_expectation"),
            professional_badges=data.get("professional_badges", []),
            qualitative_profile=data.get("qualitative_profile", []),
        )


SAI_ENDPOINT = os.getenv(
    "SAI_ENDPOINT",
    "https://sai-library.saiapplications.com/api/templates/69f263ac4b33fbdc46ebeb55/execute",
)
SAI_API_KEY = os.getenv("SAI_API_KEY", "")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    # Spanish / Portuguese variants
    "ene": 1, "abr": 4, "ago": 8, "dic": 12, "fev": 2, "mai": 5, "set": 9, "out": 10, "dez": 12,
}


def _parse_period_to_months(period: str) -> tuple[int, int] | None:
    """Parse a period string like 'Jan. 2023 – Apr. 2024' or '2021 – Present'
    into (start, end) absolute month numbers (year*12 + month). Returns None if unparseable."""
    import re
    from datetime import date

    if not period:
        return None

    now = date.today()
    now_months = now.year * 12 + now.month

    # Split on any dash variant or 'to'
    parts = re.split(r"\s*(?:[\-‒–—―]|to|a)\s+", period.strip(), maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        # Single date — can't compute a range
        return None

    def parse_point(s: str, default_month: int) -> int | None:
        s = s.strip().lower()
        if any(k in s for k in ("present", "current", "now", "actual", "atual", "presente", "hoy", "hoje", "today")):
            return now_months
        # Month name + year
        m = re.search(r"([a-z]{3,})\.?\s*,?\s*(\d{4})", s)
        if m:
            mon = MONTHS.get(m.group(1)[:3])
            if mon:
                return int(m.group(2)) * 12 + mon
        # Numeric MM/YYYY or MM-YYYY
        m = re.search(r"(\d{1,2})\s*[/\-.]\s*(\d{4})", s)
        if m and 1 <= int(m.group(1)) <= 12:
            return int(m.group(2)) * 12 + int(m.group(1))
        # Bare year
        m = re.search(r"(\d{4})", s)
        if m:
            return int(m.group(1)) * 12 + default_month
        return None

    start = parse_point(parts[0], default_month=1)
    end   = parse_point(parts[1], default_month=12)
    if start is None or end is None or end < start:
        return None
    return (start, min(end, now_months))


def _compute_years_of_experience(experience: list[dict]) -> int | None:
    """Merge all experience periods (overlaps counted once) and return total years, floored."""
    intervals = []
    for exp in experience or []:
        rng = _parse_period_to_months(exp.get("period", ""))
        if rng:
            intervals.append(rng)

    if not intervals:
        return None

    intervals.sort()
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1] + 1:   # contiguous or overlapping
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    total_months = sum(end - start + 1 for start, end in merged)
    return total_months // 12


class AgentClient:
    def __init__(self):
        self._groq_key   = os.getenv("GROQ_API_KEY", "")
        self._gemini_key = os.getenv("GEMINI_API_KEY", "")

    def extract_candidate_data(self, cv_text: str) -> CandidateData:
        """Provider chain: Gemini → SAI → Groq. Falls through on any failure."""
        candidate = self._extract(cv_text)

        # Show ONLY the experience deterministically computed from the dated
        # work history. We deliberately ignore (a) the LLM's own arithmetic,
        # which is unreliable, and (b) any self-declared total the candidate
        # states without dated backing (e.g. "5+ years"). If no period parses,
        # leave it at 0 so the generators hide the figure rather than guess.
        candidate.years_of_experience = _compute_years_of_experience(candidate.experience) or 0

        return candidate

    def _extract(self, cv_text: str) -> CandidateData:
        errors = []

        if self._gemini_key:
            try:
                return self._extract_via_gemini(cv_text)
            except Exception as e:
                errors.append(f"Gemini: {e}")
                print(f"[AgentClient] Gemini failed ({e}), trying next provider.")

        if SAI_API_KEY:
            try:
                return self._extract_via_sai(cv_text)
            except Exception as e:
                errors.append(f"SAI: {e}")
                print(f"[AgentClient] SAI failed ({e}), falling back to Groq.")

        if not self._groq_key:
            raise ValueError(
                "No AI provider available. " + (" | ".join(errors) if errors else "No API keys configured.")
            )

        try:
            return self._extract_via_groq(cv_text)
        except Exception as e:
            errors.append(f"Groq: {e}")
            raise RuntimeError("All providers failed → " + " | ".join(errors)) from e

    # ── Gemini ──────────────────────────────────────────────────────────────
    def _extract_via_gemini(self, cv_text: str) -> CandidateData:
        # Gemini has a 1M-token context window — no compression needed.
        payload = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {"parts": [{"text": f"Extract the candidate data from the following documents:\n\n{cv_text}"}]}
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 32768,
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }
        for attempt in range(2):
            resp = requests.post(
                GEMINI_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                params={"key": self._gemini_key},
                timeout=90,
            )
            if resp.status_code in (429, 500, 503) and attempt == 0:
                import time
                print(f"[AgentClient] Gemini transient {resp.status_code}, retrying in 5s")
                time.sleep(5)
                continue
            resp.raise_for_status()
            break

        body = resp.json()
        raw = body["candidates"][0]["content"]["parts"][0]["text"]
        raw = self._clean_json(raw)
        data = json.loads(raw)
        return CandidateData.from_dict(data)

    # ── SAI ───────────────────────────────────────────────────────────────
    def _extract_via_sai(self, cv_text: str) -> CandidateData:
        headers = {
            "X-API-KEY":    SAI_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {"inputs": {"resume": cv_text}}

        resp = requests.post(SAI_ENDPOINT, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()

        body = resp.json()

        # SAI may return the JSON directly or nested under an output key
        raw = None
        if isinstance(body, dict):
            # Try common wrapper keys first
            for key in ("output", "result", "response", "content", "text"):
                if key in body and isinstance(body[key], str):
                    raw = body[key]
                    break
            if raw is None:
                # Assume the body itself is the candidate JSON
                raw_candidate = body
                return CandidateData.from_dict(raw_candidate)

        if raw is None and isinstance(body, str):
            raw = body

        if not raw:
            raise ValueError(f"Unexpected SAI response format: {str(body)[:200]}")

        raw = self._clean_json(raw)
        data = json.loads(raw)
        return CandidateData.from_dict(data)

    # ── Groq ──────────────────────────────────────────────────────────────
    def _extract_via_groq(self, cv_text: str) -> CandidateData:
        headers = {
            "Authorization": f"Bearer {self._groq_key}",
            "Content-Type":  "application/json",
        }

        # Groq free tier: ~12k tokens/minute TOTAL (input + output).
        # Budget: system ~2k + input ~3k (12k chars) + output 6k ≈ 11k.
        CHAR_LIMIT = 12_000
        text = self._compress_cv(cv_text, CHAR_LIMIT)

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"Extract the candidate data from the following documents:\n\n{text}"},
            ],
            "temperature": 0.1,
            "max_tokens":  6000,
        }

        for attempt in range(2):
            resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=120)
            if resp.status_code == 429 and attempt == 0:
                wait = int(resp.headers.get("retry-after", 20))
                wait = min(wait, 25)
                print(f"[AgentClient] Groq rate limited, retrying in {wait}s")
                import time; time.sleep(wait)
                continue
            resp.raise_for_status()
            break

        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = self._clean_json(raw)
        data = json.loads(raw)
        return CandidateData.from_dict(data)

    @staticmethod
    def _compress_cv(text: str, max_chars: int) -> str:
        """For CVs over max_chars, keep only the first description line per experience."""
        import re
        if len(text) <= max_chars:
            return text

        # Any Unicode dash variant pdfplumber might produce
        DASH = r'[\-‒–—―]'

        lines = text.split('\n')
        compressed = []
        in_description = False
        desc_lines_kept = 0

        for line in lines:
            stripped = line.strip()

            if not stripped:
                in_description = False
                compressed.append(line)
                continue

            # Section header: starts with digit(s) and has a dash in first 10 chars
            # e.g. "4 –", "5.0–", "5.1 – Chimica"
            is_section = bool(re.match(r'^\d', stripped)) and bool(
                re.search(DASH, stripped[:10])
            )

            # Job description marker
            is_job_desc = bool(re.match(r'^Job\s+[Dd]escription', stripped))

            if is_section:
                in_description = False
                desc_lines_kept = 0
                compressed.append(line)
            elif is_job_desc:
                in_description = True
                desc_lines_kept = 0
                compressed.append(line)
            elif in_description:
                if desc_lines_kept < 1:
                    compressed.append(line)
                    desc_lines_kept += 1
                # else: skip
            else:
                compressed.append(line)

        result = '\n'.join(compressed)
        print(f"[AgentClient] CV compressed: {len(text)} → {len(result)} chars")
        return result[:max_chars]

    @staticmethod
    def _clean_json(text: str) -> str:
        """Strip markdown fences if present."""
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        return text.strip()
