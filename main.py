import os
import tempfile
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
async def extract_cv(file: UploadFile = File(...)):
    """
    Receives a CV PDF, extracts text, calls the SAI agent,
    and returns structured candidate data as JSON.
    PDF generation happens client-side (Streamlit).
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Extract text
    try:
        from modules.pdf_extractor import extract_text_from_bytes
        cv_text = extract_text_from_bytes(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"PDF extraction failed: {e}")

    if not cv_text or len(cv_text.strip()) < 50:
        raise HTTPException(status_code=422, detail="Could not extract readable text from PDF.")

    # Call SAI agent
    try:
        from modules.agent_client import AgentClient
        candidate = AgentClient().extract_candidate_data(cv_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent extraction failed: {e}")

    return JSONResponse(asdict(candidate))
