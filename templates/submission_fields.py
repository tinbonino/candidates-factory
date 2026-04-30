"""
Fields for the Candidate Submission Form.
Structure mirrors CANDIDATE SUBMISSION FORM 2.docx exactly.
"""

# Sections and fields in document order.
# Each entry: {"section": str, "key": str, "label": str}
# "key" maps to a CandidateData attribute (or nested resolution in the generator).

SUBMISSION_SECTIONS = [
    {
        "title": "1. PROFESSIONAL SUMMARY",
        "fields": [
            {"key": "display_name",         "label": "Candidate Name"},
            {"key": "years_of_experience",  "label": "Total Years of Experience"},
            {"key": "core_expertise",       "label": "Core Expertise"},
            {"key": "key_industries",       "label": "Key Industries"},
            {"key": "technical_highlights", "label": "Technical Highlights"},
            {"key": "integration_skills",   "label": "Integration Skills"},
        ],
    },
    {
        "title": "2. EDUCATION & CERTIFICATIONS",
        "fields": [
            {"key": "education",      "label": "Higher Education"},
            {"key": "certifications", "label": "Official Certifications"},
            {"key": "key_training",   "label": "Key Training"},
        ],
    },
    {
        "title": "3. LANGUAGES",
        "fields": [
            {"key": "lang_english",    "label": "English"},
            {"key": "lang_portuguese", "label": "Portuguese"},
            {"key": "lang_spanish",    "label": "Spanish"},
        ],
    },
    {
        "title": "4. TECHNICAL EVALUATION (SAI RATINGS)",
        "fields": [
            {"key": "overall_rating",     "label": "Overall Rating"},
            {"key": "technical_accuracy", "label": "Technical Accuracy"},
            {"key": "key_strengths",      "label": "Key Strengths"},
            {"key": "areas_for_growth",   "label": "Areas for Growth"},
        ],
    },
    {
        "title": "5. PROFESSIONAL EXPERIENCE (HIGHLIGHTS)",
        "fields": [],  # rendered separately as experience list
    },
    {
        "title": "6. RECRUITER LOGISTICS & STATUS",
        "fields": [
            {"key": "current_location",      "label": "Current Location"},
            {"key": "work_model",            "label": "Work Model"},
            {"key": "visa_status",           "label": "Visa Status"},
            {"key": "availability",          "label": "Availability"},
            {"key": "interview_availability","label": "Interview Availability"},
            {"key": "salary_expectation",    "label": "Expected Salary"},
            {"key": "recruiter_comments",    "label": "Recruiter Comments"},
        ],
    },
]
