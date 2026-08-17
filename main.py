import os
import tempfile
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
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
