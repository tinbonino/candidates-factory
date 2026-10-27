import os
import base64
import tempfile
import zipfile
import io
import requests as _requests
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from dataclasses import asdict
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Candidates Factory API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ──────────────────────────────────────────────────────────────────────
APP_PASSWORD       = os.getenv("APP_PASSWORD", "")
PA_WEBHOOK_URL     = os.getenv("POWER_AUTOMATE_WEBHOOK_URL", "")
_bearer            = HTTPBearer(auto_error=False)

async def _require_auth(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    if not APP_PASSWORD:
        return  # no password configured → open access
    if not creds or creds.credentials != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/extract")
async def extract_cv(
    files: List[UploadFile] = File(...),
    jd: Optional[UploadFile] = File(None),
):
    """
    Receives one or more PDFs (resume + optional technical tests) and an
    optional Job Description PDF (`jd`). Extracts and combines the candidate
    text, and — when a JD is provided — tailors the structured output to
    emphasize the experience most relevant to that role (without fabricating).
    Returns structured candidate data as JSON.
    """
    from modules.pdf_extractor import extract_text_from_bytes

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files are accepted. Got: {f.filename}"
            )

    # Character limits per document to stay within model context limits.
    # llama-3.3-70b-versatile supports 128k tokens; ~4 chars per token.
    CV_CHAR_LIMIT  = 100_000
    DOC_CHAR_LIMIT = 30_000
    JD_CHAR_LIMIT  = 20_000

    # Extract and label text from each file
    # First file is always the CV/resume; the rest are supplementary documents
    sections = []
    for i, upload in enumerate(files):
        pdf_bytes = await upload.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail=f"File '{upload.filename}' is empty.")

        try:
            text = extract_text_from_bytes(pdf_bytes)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"PDF extraction failed for '{upload.filename}': {e}")

        if not text or len(text.strip()) < 20:
            raise HTTPException(status_code=422, detail=f"Could not extract readable text from '{upload.filename}'.")

        # Truncate to avoid exceeding Groq's payload limit
        limit = CV_CHAR_LIMIT if i == 0 else DOC_CHAR_LIMIT
        if len(text) > limit:
            text = text[:limit] + "\n\n[... document truncated for processing ...]"

        label = "RESUME / CV" if i == 0 else f"SUPPLEMENTARY DOCUMENT: {upload.filename}"
        sections.append(f"=== {label} ===\n{text}")

    combined_text = "\n\n".join(sections)

    # Optional Job Description — used to tailor the emphasis of the output.
    jd_text = None
    if jd is not None and jd.filename:
        if not jd.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Job Description must be a PDF. Got: {jd.filename}",
            )
        jd_bytes = await jd.read()
        if jd_bytes:
            try:
                jd_text = extract_text_from_bytes(jd_bytes)
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"JD extraction failed for '{jd.filename}': {e}")
            if jd_text and len(jd_text.strip()) >= 20:
                jd_text = jd_text[:JD_CHAR_LIMIT]
            else:
                jd_text = None  # unreadable JD → just process without tailoring

    # Call AI agent with combined text (+ optional JD tailoring)
    try:
        from modules.agent_client import AgentClient
        candidate = AgentClient().extract_candidate_data(combined_text, jd_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent extraction failed: {e}")

    try:
        return JSONResponse(asdict(candidate))
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Response serialization failed: {e}\n{traceback.format_exc()[-1500:]}",
        )


# ── HTML frontend ─────────────────────────────────────────────────────────────
@app.get("/")
def index():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    return HTMLResponse("<h1>index.html not found</h1>", status_code=404)


@app.post("/api/auth")
def auth(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
):
    """Validate APP_PASSWORD and return ok/unauthorized."""
    if not APP_PASSWORD:
        return {"ok": True}
    if not creds or creds.credentials != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    return {"ok": True}


@app.post("/api/process")
async def process_cv(
    files: List[UploadFile] = File(...),
    jd: Optional[UploadFile] = File(None),
    vacancy_folder: Optional[str] = Form(None),
    _auth=Depends(_require_auth),
):
    """
    Full pipeline: extract → generate PDFs → (optional) upload to SharePoint via
    Power Automate.  Returns JSON with candidate name, SP status, and base64 ZIP.
    vacancy_folder: relative path inside 'Vacancy Files/', e.g.
        'Abiomed/CSV Validation Engineer 2026-09-16'
    """
    from modules.pdf_extractor import extract_text_from_bytes

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    CV_CHAR_LIMIT  = 100_000
    DOC_CHAR_LIMIT = 30_000
    JD_CHAR_LIMIT  = 20_000

    sections = []
    for i, upload in enumerate(files):
        pdf_bytes = await upload.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail=f"File '{upload.filename}' is empty.")
        try:
            text = extract_text_from_bytes(pdf_bytes)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"PDF extraction failed: {e}")
        if not text or len(text.strip()) < 20:
            raise HTTPException(status_code=422, detail=f"Could not extract text from '{upload.filename}'.")
        limit = CV_CHAR_LIMIT if i == 0 else DOC_CHAR_LIMIT
        if len(text) > limit:
            text = text[:limit] + "\n\n[... document truncated ...]"
        label = "RESUME / CV" if i == 0 else f"SUPPLEMENTARY DOCUMENT: {upload.filename}"
        sections.append(f"=== {label} ===\n{text}")

    combined_text = "\n\n".join(sections)

    jd_text = None
    if jd is not None and jd.filename:
        jd_bytes = await jd.read()
        if jd_bytes:
            try:
                jd_text = extract_text_from_bytes(jd_bytes)
                if jd_text and len(jd_text.strip()) >= 20:
                    jd_text = jd_text[:JD_CHAR_LIMIT]
                else:
                    jd_text = None
            except Exception:
                jd_text = None

    try:
        from modules.agent_client import AgentClient
        candidate = AgentClient().extract_candidate_data(combined_text, jd_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent extraction failed: {e}")

    # Generate PDFs
    try:
        from modules.generators import infographic, submission_form, branded_resume
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = {
                "infographic":     os.path.join(tmpdir, "infographic.pdf"),
                "submission_form": os.path.join(tmpdir, "submission_form.pdf"),
                "resume_branded":  os.path.join(tmpdir, "resume_branded.pdf"),
            }
            infographic.generate(candidate, paths["infographic"])
            submission_form.generate(candidate, paths["submission_form"])
            branded_resume.generate(candidate, paths["resume_branded"])
            pdfs = {k: open(v, "rb").read() for k, v in paths.items()}
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}\n{traceback.format_exc()[-1000:]}")

    # Power Automate upload (optional)
    sp_status = _trigger_power_automate(candidate.display_name, vacancy_folder, pdfs)

    # Build ZIP in memory
    safe = candidate.display_name.replace(" ", "_").replace(".", "")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"infographic_{safe}.pdf",          pdfs["infographic"])
        zf.writestr(f"submission_form_{safe}.pdf",       pdfs["submission_form"])
        zf.writestr(f"Stefanini_resume_{safe}.pdf",      pdfs["resume_branded"])
    buf.seek(0)

    return JSONResponse({
        "candidate_name": candidate.display_name,
        "candidate_title": candidate.title or "",
        "sharepoint": sp_status,
        "zip_b64": base64.b64encode(buf.getvalue()).decode(),
        "files": {
            "infographic":     base64.b64encode(pdfs["infographic"]).decode(),
            "submission_form": base64.b64encode(pdfs["submission_form"]).decode(),
            "resume_branded":  base64.b64encode(pdfs["resume_branded"]).decode(),
        },
    })


def _trigger_power_automate(
    candidate_name: str,
    vacancy_folder: Optional[str],
    pdfs: dict,
) -> dict:
    """POST candidate PDFs to the Power Automate HTTP trigger. Returns status dict."""
    if not PA_WEBHOOK_URL:
        return {"status": "skipped", "reason": "POWER_AUTOMATE_WEBHOOK_URL not configured"}
    if not vacancy_folder or not vacancy_folder.strip():
        return {"status": "skipped", "reason": "No vacancy folder provided"}

    folder = vacancy_folder.strip("/")
    # Normalise: prepend 'Vacancy Files/' if not already there
    if not folder.startswith("Vacancy Files/"):
        folder = f"Vacancy Files/{folder}"

    payload = {
        "candidate_name":  candidate_name,
        "vacancy_folder":  folder,         # e.g. "Vacancy Files/Abiomed/CSV Validation Engineer 2026-09-16"
        "sharepoint_site": "https://stefaninilatam.sharepoint.com/sites/LDHTalentTeam",
        "files": {
            k: base64.b64encode(v).decode() for k, v in pdfs.items()
        },
    }

    try:
        resp = _requests.post(PA_WEBHOOK_URL, json=payload, timeout=20)
        resp.raise_for_status()
        return {"status": "uploaded", "folder": f"{folder}/Candidates Files/{candidate_name}"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
