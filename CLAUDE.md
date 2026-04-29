# Candidates Factory

## Project Overview

A web application that automates CV processing for Stefanini's LDH (Latam Digital Hub) recruitment team. It receives a candidate's CV in PDF, extracts data using an AI agent, generates three branded documents, and stores them in OneDrive.

## Core Workflow

1. User uploads a CV (PDF) via the Streamlit frontend (or POST to the API endpoint)
2. Text is extracted from the PDF
3. An AI agent processes the text and returns structured candidate data
4. Three PDF documents are generated
5. All files are uploaded to a candidate-specific OneDrive folder

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Backend / API | FastAPI |
| PDF extraction | `pdfplumber` |
| AI Agent | Custom adapter (`AgentClient`) — config TBD |
| PDF generation | `ReportLab` + `Pillow` |
| OneDrive storage | Microsoft Graph API via `msal` |
| Config | `python-dotenv` |

## Project Structure

```
candidates-factory/
├── CLAUDE.md
├── app.py                        # Streamlit UI
├── main.py                       # FastAPI app + /api/process-cv endpoint
├── .env                          # API keys and config (never commit)
├── requirements.txt
├── assets/
│   └── ldh_logo.png              # LDH Latam Digital Hub by Stefanini logo
├── modules/
│   ├── pdf_extractor.py          # PDF text extraction (pdfplumber)
│   ├── agent_client.py           # AI agent abstraction layer
│   ├── generators/
│   │   ├── infographic.py        # Visual talent card PDF
│   │   ├── submission_form.py    # Submission form PDF
│   │   └── branded_resume.py     # Anonymized Stefanini-branded resume PDF
│   └── onedrive.py               # Microsoft Graph API upload
└── templates/
    └── submission_fields.py      # Defines which fields go in the submission form
```

## Output Documents

### 1. Infographic PDF (talent card)
- Visual one-pager for presenting the candidate to the client
- Header with LDH logo
- Sections: summary, top skills (visual bars), experience timeline, languages, certifications
- Color palette: Stefanini blue `#003087`, orange `#FF6B00`
- Language: English
- Reference file: `Infographic.pdf` (user provided — visual reference, not a strict template)

### 2. Submission Form PDF
- Structured form with specific fields extracted from the CV
- Fields defined in `templates/submission_fields.py`
- **Pending**: final field list to be confirmed (original form: `CANDIDATE SUBMISSION FORM 2.docx`)
- Language: English

### 3. Branded Resume PDF
- Full CV reformatted with Stefanini/LDH branding
- Header: LDH logo
- **Anonymization rules**:
  - Last name replaced by its initial (e.g., "Juan Martinez" → "Juan M.")
  - Remove all identifying contact info: email, phone, LinkedIn URL, physical address
- Typography and colors match corporate brand
- Language: English

## AI Agent Integration

The agent is accessed through an abstraction layer so the underlying provider can be swapped without touching the rest of the app.

```python
# modules/agent_client.py
class AgentClient:
    def extract_candidate_data(self, cv_text: str) -> CandidateData:
        ...  # pluggable implementation
```

**Structured output schema** (what the agent must return):
```json
{
  "first_name": "string",
  "last_name": "string",
  "last_name_initial": "string",    // e.g. "M."
  "title": "string",                // professional title / role
  "summary": "string",              // executive summary (AI-generated)
  "skills": ["string"],
  "languages": [{"lang": "string", "level": "string"}],
  "experience": [
    {
      "company": "string",
      "role": "string",
      "period": "string",
      "description": "string",
      "achievements": ["string"]
    }
  ],
  "education": [
    {
      "institution": "string",
      "degree": "string",
      "year": "string"
    }
  ],
  "certifications": ["string"],
  "years_of_experience": "number",
  "availability": "string",         // if present in CV
  "salary_expectation": "string"    // if present in CV
}
```

**Agent API config**: to be provided by the user. When received, implement in `modules/agent_client.py`.

## OneDrive Storage

- Account type: **Corporate Microsoft 365**
- Azure AD app: **not yet registered** — needs to be created before OneDrive integration can be tested
- Folder structure: `Candidates Factory/{First Name} {Last Name Initial}/`
  - Example: `Candidates Factory/Juan M./`
- Files stored per candidate:
  - `infographic.pdf`
  - `submission_form.pdf`
  - `resume_branded.pdf`

### Azure AD App Setup (pending)
Required steps before OneDrive works:
1. Register an app in Azure AD (portal.azure.com)
2. Grant permission: `Files.ReadWrite` (Microsoft Graph)
3. Get: `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=          # or agent-specific key
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_TENANT_ID=
ONEDRIVE_ROOT_FOLDER=Candidates Factory
```

## API Endpoint

```
POST /api/process-cv
  Content-Type: multipart/form-data
  Body: file (PDF)

  Response 200:
  {
    "candidate_name": "Juan M.",
    "onedrive_folder": "Candidates Factory/Juan M./",
    "files": {
      "infographic": "<onedrive_link>",
      "submission_form": "<onedrive_link>",
      "resume_branded": "<onedrive_link>"
    }
  }
```

## Brand Assets

- **Logo**: LDH Latam Digital Hub by Stefanini
  - Includes flags of: Argentina, Brazil, Chile, Colombia, Ecuador, Bolivia/El Salvador, Mexico, Panama, Peru, Honduras
  - Logo file to be placed at: `assets/ldh_logo.png`

## Pending / Open Items

- [ ] Confirm exact fields for Submission Form (review `CANDIDATE SUBMISSION FORM 2.docx`)
- [ ] Receive AI agent API config and implement `AgentClient`
- [ ] Register Azure AD app and get credentials
- [ ] Get final LDH logo file (`assets/ldh_logo.png`)
- [ ] Confirm infographic layout (user to describe sections or provide a cleaner reference)
- [ ] Define if salary/availability fields are mandatory or optional in the form
