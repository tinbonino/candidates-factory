"""
AgentClient — uses Groq (llama-3.3-70b-versatile) to extract structured candidate data from CV text.
"""
import json
import os
from dataclasses import dataclass, field
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

SYSTEM_PROMPT = """You are an expert HR analyst working for LDH Latam Digital Hub by Stefanini. Your task is to analyze one or more documents about a candidate and return a single, valid JSON object with structured data AND a qualitative profile analysis. You never explain, comment, or add any text outside the JSON.

The input may contain:
- A RESUME / CV section (always present, primary source of structured data)
- One or more SUPPLEMENTARY DOCUMENT sections (e.g. technical tests, assessments) — use these to enrich technical_highlights, key_strengths, areas_for_growth, overall_rating, technical_accuracy, and the qualitative analysis. Do not extract personal or contact data from supplementary documents.

OUTPUT RULES:
- Return ONLY a raw JSON object — no markdown, no code fences, no explanation
- All text fields must be in English (translate if the CV is in another language)
- Never include contact information: no emails, phone numbers, LinkedIn URLs, or physical addresses
- If a field is not found in the CV, infer it where possible or return null

ANONYMIZATION:
- last_name_initial must be the first letter of last_name followed by a period (e.g. "Martinez" → "M.")
- Never include the full last name in the summary or any other field

REQUIRED JSON SCHEMA:
{
  "first_name": "string",
  "last_name": "string",
  "last_name_initial": "string",
  "title": "string — current or most recent professional role",
  "summary": "string — 3 to 5 sentence executive summary written in third person, synthesized from the full CV",
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
      "description": "string — one to two sentence summary of responsibilities",
      "achievements": ["string — specific, quantified achievements when available"]
    }
  ],
  "education": [{"institution": "string", "degree": "string", "year": "string"}],
  "certifications": ["string"],
  "years_of_experience": "number",
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
        return f"{self.first_name} {self.last_name_initial}"

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


class AgentClient:
    def __init__(self):
        self._groq_key = os.getenv("GROQ_API_KEY", "")

    def extract_candidate_data(self, cv_text: str) -> CandidateData:
        """Try SAI first; fall back to Groq if SAI fails for any reason."""

        if SAI_API_KEY:
            try:
                return self._extract_via_sai(cv_text)
            except Exception as e:
                print(f"[AgentClient] SAI failed ({e}), falling back to Groq.")

        if not self._groq_key:
            raise ValueError("No AI provider available: SAI_API_KEY and GROQ_API_KEY are both missing.")

        return self._extract_via_groq(cv_text)

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

        # For very long CVs, compress before sending to avoid 413.
        CHAR_LIMIT = 20_000
        text = self._compress_cv(cv_text, CHAR_LIMIT)

        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"Extract the candidate data from the following documents:\n\n{text}"},
            ],
            "temperature": 0.1,
            "max_tokens":  4096,
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
