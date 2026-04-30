"""
AgentClient — calls the SAI external AI agent to extract structured candidate data from CV text.

Endpoint : POST https://sai-library.saiapplications.com/api/templates/69f263ac4b33fbdc46ebeb55/batch
Request  : { "resume": "<cv_text>" }
Auth     : x-api-key header
"""
import json
import os
from dataclasses import dataclass, field
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

AGENT_URL = "https://sai-library.saiapplications.com/api/templates/69f263ac4b33fbdc46ebeb55/execute"


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
            years_of_experience=int(data.get("years_of_experience", 0)),
            availability=data.get("availability"),
            salary_expectation=data.get("salary_expectation"),
        )


class AgentClient:
    def __init__(self):
        self._api_key = os.getenv("AGENT_API_KEY")
        if not self._api_key:
            raise ValueError("AGENT_API_KEY must be set in .env")

    def extract_candidate_data(self, cv_text: str) -> CandidateData:
        headers = {
            "x-api-key": self._api_key,
            "Content-Type": "application/json",
        }
        payload = {"inputs": {"resume": cv_text}}

        resp = requests.post(AGENT_URL, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()

        raw = self._parse_response(resp.json())
        return CandidateData.from_dict(raw)

    def _parse_response(self, resp_data) -> dict:
        """
        Extracts the JSON candidate data from the agent response.
        Handles common response envelope patterns.
        """
        # If the response is already a dict with candidate fields
        if isinstance(resp_data, dict):
            # Direct response
            if "first_name" in resp_data:
                return resp_data
            # Wrapped in a result/data/output key
            for key in ("result", "data", "output", "response", "content"):
                if key in resp_data:
                    val = resp_data[key]
                    if isinstance(val, str):
                        return self._extract_json(val)
                    if isinstance(val, dict):
                        return val

        # Batch endpoint may return a list
        if isinstance(resp_data, list) and resp_data:
            first = resp_data[0]
            if isinstance(first, dict):
                if "first_name" in first:
                    return first
                for key in ("result", "data", "output", "response", "content"):
                    if key in first:
                        val = first[key]
                        if isinstance(val, str):
                            return self._extract_json(val)
                        if isinstance(val, dict):
                            return val

        # Fallback: treat the whole response as a string and extract JSON
        return self._extract_json(json.dumps(resp_data))

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Strips markdown fences and parses the first JSON object found."""
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        # Find first { ... }
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        return json.loads(text)
