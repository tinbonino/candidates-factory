import os
import tempfile
from typing import List
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
async def extract_cv(files: List[UploadFile] = File(...)):
    """
    Receives one or more PDFs (resume + optional technical tests),
    extracts and combines their text, calls the AI agent,
    and returns structured candidate data as JSON.
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

    # Character limits per document to stay within Groq's payload limit.
    # ~20k chars ≈ 5k tokens. CV gets more budget than supplementary docs.
    CV_CHAR_LIMIT  = 20_000
    DOC_CHAR_LIMIT = 10_000

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

    # Call AI agent with combined text
    try:
        from modules.agent_client import AgentClient
        candidate = AgentClient().extract_candidate_data(combined_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent extraction failed: {e}")

    return JSONResponse(asdict(candidate))
