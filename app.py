import io
import os
import base64
import zipfile
import tempfile
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Candidates Factory — LDH",
    page_icon="📄",
    layout="centered",
)

# ── Authentication ─────────────────────────────────────────────────────────────
from modules.auth import require_auth, logout
user = require_auth()

# ── Brand CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Primary buttons → Stefanini orange */
    .stButton > button[kind="primary"] {
        background-color: #FF6B00 !important;
        border-color:     #FF6B00 !important;
        color: white !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #e05e00 !important;
        border-color:     #e05e00 !important;
    }
    /* Download buttons */
    .stDownloadButton > button {
        background-color: #003087 !important;
        border-color:     #003087 !important;
        color: white !important;
    }
    .stDownloadButton > button:hover {
        background-color: #002060 !important;
        border-color:     #002060 !important;
    }
    /* Headings */
    h1, h2, h3 { color: #003087 !important; }
    /* Divider accent */
    hr { border-color: #FF6B00 !important; }
</style>
""", unsafe_allow_html=True)

# ── Branded header ─────────────────────────────────────────────────────────────
_logo_path = os.path.join(os.path.dirname(__file__), "logos", "StefaniniGroup_Logo-02.png")
_logo_html = ""
if os.path.exists(_logo_path):
    with open(_logo_path, "rb") as _f:
        _b64 = base64.b64encode(_f.read()).decode()
    _logo_html = f'<img src="data:image/png;base64,{_b64}" style="height:48px;">'

st.markdown(f"""
<div style="
    background-color: #003087;
    padding: 18px 28px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    margin-bottom: 8px;
">
    {_logo_html}
    <div style="margin-left: 20px; color: white; border-left: 3px solid #FF6B00; padding-left: 16px;">
        <div style="font-size: 20px; font-weight: 700; letter-spacing: 0.5px;">Candidates Factory</div>
        <div style="font-size: 12px; opacity: 0.80; margin-top: 2px;">LDH Latam Digital Hub by Stefanini</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── User info + logout ────────────────────────────────────────────────────────
col1, col2 = st.columns([4, 1])
col1.caption(f"👤 {user['name']}")
if col2.button("Cerrar sesión", use_container_width=True):
    logout()

# ── Config ────────────────────────────────────────────────────────────────────
API_URL          = os.getenv("API_URL", "").rstrip("/")
GROQ_API_KEY     = os.getenv("GROQ_API_KEY", "")
agent_configured = bool(GROQ_API_KEY and API_URL)

SHAREPOINT_SITE_URL  = os.getenv("SHAREPOINT_SITE_URL", "")
AZURE_CLIENT_ID      = os.getenv("AZURE_CLIENT_ID", "")
sharepoint_configured = bool(SHAREPOINT_SITE_URL and AZURE_CLIENT_ID)

# ── Session state init ────────────────────────────────────────────────────────
for key in ("pdfs", "display_name", "candidate_info", "last_file", "sharepoint_links"):
    if key not in st.session_state:
        st.session_state[key] = None


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


def _make_zip(pdfs, display_name) -> bytes:
    safe = display_name.replace(" ", "_")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"infographic_{safe}.pdf",     pdfs["infographic"])
        zf.writestr(f"submission_form_{safe}.pdf",  pdfs["submission_form"])
        resume_safe = f"Stefanini_resume_{display_name.replace(' ', '_').replace('.', '')}"
        zf.writestr(f"{resume_safe}.pdf",            pdfs["resume_branded"])
    buf.seek(0)
    return buf.getvalue()


def _upload_to_sharepoint(pdfs, display_name) -> dict | None:
    """Upload PDFs to SharePoint. Returns links dict or None on failure."""
    try:
        from modules.onedrive import upload_candidate_files
        return upload_candidate_files(display_name, pdfs)
    except Exception as e:
        st.warning(f"⚠️ No se pudo subir a SharePoint: {e}")
        return None


def _download_buttons(pdfs, display_name):
    st.success(f"✅ Documentos generados para **{display_name}**")
    safe = display_name.replace(" ", "_")

    # ── Individual downloads ───────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.download_button(
        "📊 Infographic",
        data=pdfs["infographic"],
        file_name=f"infographic_{safe}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary",
        key="dl_infographic",
    )
    c2.download_button(
        "📋 Submission Form",
        data=pdfs["submission_form"],
        file_name=f"submission_form_{safe}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary",
        key="dl_submission",
    )
    c3.download_button(
        "📄 Branded Resume",
        data=pdfs["resume_branded"],
        file_name=f"Stefanini_resume_{display_name.replace(' ', '_').replace('.', '')}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary",
        key="dl_resume",
    )

    st.divider()

    # ── ZIP download ───────────────────────────────────────────────────────
    zip_bytes = _make_zip(pdfs, display_name)
    st.download_button(
        "⬇️ Descargar los 3 documentos en un ZIP",
        data=zip_bytes,
        file_name=f"LDH_{safe}_docs.zip",
        mime="application/zip",
        use_container_width=True,
        key="dl_zip",
    )

    # ── SharePoint links ───────────────────────────────────────────────────
    links = st.session_state.get("sharepoint_links")
    if links:
        st.divider()
        st.markdown("**📁 Archivos en SharePoint:**")
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"[📊 Infographic]({links['infographic']})")
        col2.markdown(f"[📋 Submission Form]({links['submission_form']})")
        col3.markdown(f"[📄 Branded Resume]({links['resume_branded']})")


def _clear_results():
    for key in ("pdfs", "display_name", "candidate_info", "last_file", "sharepoint_links"):
        st.session_state[key] = None


# ── MAIN ──────────────────────────────────────────────────────────────────────
if agent_configured:
    # ── AUTO MODE ─────────────────────────────────────────────────────────────
    st.markdown("### Subí los documentos del candidato")
    st.caption("El primer archivo debe ser el CV/Resume. Podés agregar tests técnicos u otros documentos adicionales.")
    uploaded_files = st.file_uploader(
        "Formato PDF", type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    # Reset results when file selection changes
    files_key = ",".join(sorted(f.name for f in uploaded_files)) if uploaded_files else ""
    if files_key and st.session_state["last_file"] != files_key:
        _clear_results()
        st.session_state["last_file"] = files_key

    if uploaded_files:
        cv_file = uploaded_files[0]
        extras  = uploaded_files[1:]
        st.info(f"📄 **CV:** {cv_file.name}" + (
            f"  |  📎 **Adicionales:** {', '.join(f.name for f in extras)}" if extras else ""
        ))

        # Show Process button only when no results yet
        if st.session_state["pdfs"] is None:
            if st.button("Procesar documentos", type="primary", use_container_width=True):
                import requests
                from modules.agent_client import CandidateData

                with st.spinner("🤖 Extrayendo y procesando datos..."):
                    try:
                        files_payload = [
                            ("files", (f.name, f.getvalue(), "application/pdf"))
                            for f in uploaded_files
                        ]
                        resp = requests.post(
                            f"{API_URL}/api/extract",
                            files=files_payload,
                            timeout=120,
                        )
                        if resp.status_code != 200:
                            st.error(
                                f"Error del servidor ({resp.status_code}): {resp.text[:300]}"
                            )
                            st.stop()
                        candidate = CandidateData.from_dict(resp.json())
                    except Exception as e:
                        st.error(f"Error procesando documentos: {e}")
                        st.stop()

                with st.spinner("📄 Generando documentos..."):
                    try:
                        pdfs = _generate_pdfs(candidate)
                    except Exception as e:
                        st.error(f"Error generando PDFs: {e}")
                        st.stop()

                sp_links = None
                if sharepoint_configured:
                    with st.spinner("☁️ Subiendo a SharePoint..."):
                        sp_links = _upload_to_sharepoint(pdfs, candidate.display_name)

                # Persist results in session state
                st.session_state["pdfs"]             = pdfs
                st.session_state["display_name"]     = candidate.display_name
                st.session_state["candidate_info"]   = (
                    candidate.display_name,
                    candidate.title,
                    resp.json(),
                )
                st.session_state["sharepoint_links"] = sp_links
                st.rerun()

    # ── Show results (persisted across reruns) ────────────────────────────────
    if st.session_state["pdfs"] is not None:
        info = st.session_state["candidate_info"]
        if info:
            name, title, json_data = info
            st.markdown(f"**Candidato identificado:** {name} — {title}")
            with st.expander("Ver datos extraídos", expanded=False):
                st.json(json_data)

        _download_buttons(st.session_state["pdfs"], st.session_state["display_name"])

        st.divider()
        if st.button("🔄 Procesar otro CV", use_container_width=True):
            _clear_results()
            st.rerun()

else:
    # ── DEMO MODE ─────────────────────────────────────────────────────────────
    st.warning(
        "⚠️ El agente de IA no está configurado aún. "
        "Podés generar los documentos con un perfil de ejemplo para probar el sistema."
    )

    if st.button(
        "Generar documentos de ejemplo", type="primary", use_container_width=True
    ):
        from modules.agent_client import CandidateData

        candidate = CandidateData(
            first_name="Juan",
            last_name="Martinez",
            last_name_initial="M.",
            title="Senior Full Stack Engineer",
            summary="Juan M. is a seasoned Full Stack Engineer with over 8 years of experience building scalable web applications for enterprise clients across financial services and e-commerce. He specializes in React, Node.js, and cloud-native architectures on AWS.",
            skills=[
                "React", "Node.js", "TypeScript", "AWS", "Docker",
                "PostgreSQL", "REST APIs", "GraphQL", "Python", "Microservices",
            ],
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
                    "company": "Accenture",
                    "role": "Senior Full Stack Engineer",
                    "period": "2021 – Present",
                    "description": "Led development of a real-time trading dashboard used by 500+ financial analysts.",
                    "achievements": [
                        "Reduced page load time from 4s to 0.8s",
                        "Architected event-driven backend processing 2M+ daily transactions",
                        "Mentored team of 4 junior developers, improving sprint velocity by 30%",
                    ],
                },
                {
                    "company": "Globant",
                    "role": "Full Stack Developer",
                    "period": "2018 – 2021",
                    "description": "Built e-commerce platform features for a Fortune 500 retail client.",
                    "achievements": [
                        "Recommendation engine increasing cart conversion by 18%",
                        "REST API layer serving 10M+ monthly requests",
                    ],
                },
            ],
            education=[
                {
                    "institution": "Universidad de Buenos Aires",
                    "degree": "B.Sc. Computer Science",
                    "year": "2017",
                }
            ],
            certifications=[
                "AWS Certified Solutions Architect",
                "Google Cloud Professional",
                "Scrum Master PSM I",
            ],
            years_of_experience=8,
            availability="2 weeks notice",
            salary_expectation="USD 5,500/month",
            current_location="Buenos Aires, Argentina",
            work_model="Remote",
            visa_status="Not required",
            interview_availability="Weekdays after 5pm",
            professional_badges=[
                {
                    "title": "Cloud-Native Architecture Specialist",
                    "body": "Juan M. has led end-to-end cloud migrations on AWS, designing event-driven microservices that process over 2 million daily transactions. His hands-on expertise spans EC2, Lambda, SNS/SQS, and RDS, backed by AWS Solutions Architect certification.",
                },
                {
                    "title": "Full Stack Innovation Driver",
                    "body": "With 8+ years building production-grade React and Node.js applications, Juan M. consistently delivers measurable performance gains — including a 5× reduction in page load time for a Fortune 500 financial client.",
                },
                {
                    "title": "Agile Team Leader & Mentor",
                    "body": "Proven track record mentoring junior developers and leading cross-functional squads, improving sprint velocity by 30% at Accenture through coaching, code reviews, and process optimisation.",
                },
            ],
            qualitative_profile=[
                {
                    "title": "Global Project Leadership",
                    "body": "Juan M. has managed distributed engineering teams across Argentina and Brazil for enterprise clients including Accenture, coordinating deliverables across time zones and aligning technical roadmaps with business objectives.",
                },
                {
                    "title": "Multi-Industry Versatility",
                    "body": "High-impact delivery across Financial Services, E-Commerce, and HealthTech sectors. Juan M. adapts rapidly to domain-specific constraints — from financial compliance requirements to high-availability retail platforms serving millions of users.",
                },
                {
                    "title": "Bilingual Technical Communicator",
                    "body": "Fluent in English and Spanish, with intermediate Portuguese, enabling seamless collaboration with global stakeholders, international clients, and LATAM regional teams without communication barriers.",
                },
                {
                    "title": "Problem Solver & Clean Code Advocate",
                    "body": "Juan M. applies strong analytical thinking to complex system design challenges, consistently producing maintainable, well-documented code. His solutions are built for scale — prioritising reliability and developer experience equally.",
                },
            ],
        )

        with st.spinner("📄 Generando documentos..."):
            try:
                pdfs = _generate_pdfs(candidate)
            except Exception as e:
                st.error(f"Error generando PDFs: {e}")
                st.stop()

        st.session_state["pdfs"]         = pdfs
        st.session_state["display_name"] = candidate.display_name
        st.rerun()

    # Show demo results if already generated
    if st.session_state["pdfs"] is not None:
        _download_buttons(
            st.session_state["pdfs"],
            st.session_state["display_name"],
        )
        st.divider()
        if st.button("🔄 Generar de nuevo", use_container_width=True):
            _clear_results()
            st.rerun()

st.markdown("""
<div style="text-align:center; color:#888; font-size:11px; margin-top:16px; padding-top:8px; border-top: 1px solid #FF6B00;">
    LDH Latam Digital Hub by Stefanini — Confidential
</div>
""", unsafe_allow_html=True)
