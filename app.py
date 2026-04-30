import os
import tempfile
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Candidates Factory — LDH",
    page_icon="📄",
    layout="centered",
)

# ── Branding ──────────────────────────────────────────────────────────────────
logo_path = os.path.join(os.path.dirname(__file__), "assets", "ldh_logo.jpg")
if os.path.exists(logo_path):
    st.image(logo_path, width=180)

st.title("Candidates Factory")
st.caption("LDH Latam Digital Hub by Stefanini — CV Processing Automation")
st.divider()

# ── Helpers ───────────────────────────────────────────────────────────────────
def _generate_pdfs(candidate):
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
        return {k: open(v, "rb").read() for k, v in paths.items()}


def _download_buttons(pdfs, display_name):
    st.success(f"Documentos generados para **{display_name}**")
    c1, c2, c3 = st.columns(3)
    safe = display_name.replace(" ", "_")
    c1.download_button("📊 Infographic", data=pdfs["infographic"],
                       file_name=f"infographic_{safe}.pdf", mime="application/pdf",
                       use_container_width=True)
    c2.download_button("📋 Submission Form", data=pdfs["submission_form"],
                       file_name=f"submission_form_{safe}.pdf", mime="application/pdf",
                       use_container_width=True)
    c3.download_button("📄 Branded Resume", data=pdfs["resume_branded"],
                       file_name=f"resume_branded_{safe}.pdf", mime="application/pdf",
                       use_container_width=True)

    # OneDrive (optional)
    if all([os.getenv("AZURE_CLIENT_ID"), os.getenv("AZURE_CLIENT_SECRET"), os.getenv("AZURE_TENANT_ID")]):
        if st.button("☁️ Subir a OneDrive", use_container_width=True):
            with st.spinner("Subiendo archivos..."):
                try:
                    with tempfile.TemporaryDirectory() as td:
                        paths = {}
                        for k, b in pdfs.items():
                            p = os.path.join(td, f"{k}.pdf")
                            open(p, "wb").write(b)
                            paths[k] = p
                        from modules.onedrive import upload_candidate_files
                        links = upload_candidate_files(
                            display_name,
                            paths["infographic"], paths["submission_form"], paths["resume_branded"],
                        )
                    st.success("Archivos subidos a OneDrive!")
                    st.json(links)
                except Exception as e:
                    st.error(f"Error OneDrive: {e}")


def _sample_candidate():
    from modules.agent_client import CandidateData
    return CandidateData(
        first_name="Juan",
        last_name="Martinez",
        last_name_initial="M.",
        title="Senior Full Stack Engineer",
        summary=(
            "Juan M. is a seasoned Full Stack Engineer with over 8 years of experience building "
            "scalable web applications for enterprise clients across financial services and e-commerce. "
            "He specializes in React, Node.js, and cloud-native architectures on AWS, with a strong "
            "track record of delivering high-performance solutions under tight deadlines."
        ),
        skills=["React", "Node.js", "TypeScript", "AWS", "Docker", "PostgreSQL",
                "REST APIs", "GraphQL", "Python", "Microservices"],
        core_expertise="Full Stack development with React/Node.js and cloud-native AWS architectures",
        key_industries=["Financial Services", "E-Commerce", "HealthTech"],
        technical_highlights="Led migration of monolithic app to microservices — reduced latency 40%",
        integration_skills="REST, GraphQL, Kafka, AWS SNS/SQS",
        key_strengths="Strong problem-solving, team leadership, clean code advocate",
        areas_for_growth="Mobile development, ML/AI integration",
        overall_rating="Senior / 8.5/10",
        technical_accuracy="High — deep understanding of distributed systems",
        languages=[
            {"lang": "English",    "level": "Fluent"},
            {"lang": "Spanish",    "level": "Native"},
            {"lang": "Portuguese", "level": "Intermediate"},
        ],
        experience=[
            {
                "company": "Accenture", "role": "Senior Full Stack Engineer",
                "period": "2021 – Present",
                "description": "Led development of a real-time trading dashboard used by 500+ financial analysts.",
                "achievements": [
                    "Reduced page load time from 4s to 0.8s through code splitting and CDN optimization",
                    "Architected event-driven backend processing 2M+ daily transactions",
                    "Mentored team of 4 junior developers, improving sprint velocity by 30%",
                ],
            },
            {
                "company": "Globant", "role": "Full Stack Developer",
                "period": "2018 – 2021",
                "description": "Built e-commerce platform features for a Fortune 500 retail client.",
                "achievements": [
                    "Recommendation engine increasing cart conversion by 18%",
                    "REST API layer serving 10M+ monthly requests",
                ],
            },
        ],
        education=[
            {"institution": "Universidad de Buenos Aires", "degree": "B.Sc. Computer Science", "year": "2017"},
        ],
        certifications=["AWS Certified Solutions Architect", "Google Cloud Professional", "Scrum Master PSM I"],
        years_of_experience=8,
        availability="2 weeks notice",
        salary_expectation="USD 5,500/month",
        current_location="Buenos Aires, Argentina",
        work_model="Remote",
        visa_status="Not required",
        interview_availability="Weekdays after 5pm",
    )


# ── Main flow ─────────────────────────────────────────────────────────────────
API_URL = os.getenv("API_URL", "")          # Vercel deployment URL
agent_configured = bool(os.getenv("GROQ_API_KEY") and API_URL)

if agent_configured:
    # ── AUTO MODE — calls Vercel API which proxies to SAI ─────────────────────
    uploaded = st.file_uploader("Subí el CV del candidato (PDF)", type=["pdf"])

    if uploaded and st.button("Procesar CV", type="primary", use_container_width=True):
        import requests
        from modules.agent_client import CandidateData

        with st.spinner("Procesando CV con el agente de IA..."):
            try:
                resp = requests.post(
                    f"{API_URL.rstrip('/')}/api/extract",
                    files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                    timeout=120,
                )
                if resp.status_code != 200:
                    st.error(f"Error del servidor: {resp.status_code} — {resp.text[:300]}")
                    st.stop()
                candidate = CandidateData.from_dict(resp.json())
            except Exception as e:
                st.error(f"Error procesando CV: {e}")
                st.stop()

        with st.expander("Datos extraídos", expanded=False):
            st.json(resp.json())

        with st.spinner("Generando PDFs..."):
            try:
                pdfs = _generate_pdfs(candidate)
            except Exception as e:
                st.error(f"Error generando PDFs: {e}")
                st.stop()

        _download_buttons(pdfs, candidate.display_name)

else:
    # ── DEMO MODE (agent not configured) ──────────────────────────────────────
    st.warning(
        "El agente de IA no está configurado aún. "
        "Podés generar los documentos con un perfil de ejemplo para probar el sistema.",
        icon="⚠️",
    )

    if st.button("Generar documentos de ejemplo", type="primary", use_container_width=True):
        candidate = _sample_candidate()

        with st.spinner("Generando PDFs..."):
            try:
                pdfs = _generate_pdfs(candidate)
            except Exception as e:
                st.error(f"Error generando PDFs: {e}")
                st.stop()

        _download_buttons(pdfs, candidate.display_name)

st.divider()
st.caption("LDH Latam Digital Hub by Stefanini — Confidential")
