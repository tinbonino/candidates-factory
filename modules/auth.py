"""
Microsoft Entra ID authentication for Streamlit.
Uses OAuth 2.0 Authorization Code flow with MSAL.

Required env vars:
    AZURE_CLIENT_ID
    AZURE_CLIENT_SECRET
    AZURE_TENANT_ID
    STREAMLIT_APP_URL   e.g. https://candidates-factory.streamlit.app
"""
import os
from urllib.parse import urlencode

import msal
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_CLIENT_ID     = os.getenv("AZURE_CLIENT_ID", "")
_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
_TENANT_ID     = os.getenv("AZURE_TENANT_ID", "")
_APP_URL       = os.getenv("STREAMLIT_APP_URL", "http://localhost:8501").rstrip("/")
_REDIRECT_URI  = _APP_URL + "/"
_AUTHORITY     = f"https://login.microsoftonline.com/{_TENANT_ID}"
_SCOPES        = ["User.Read"]


def _msal_app():
    return msal.ConfidentialClientApplication(
        _CLIENT_ID,
        authority=_AUTHORITY,
        client_credential=_CLIENT_SECRET,
    )


def _build_auth_url() -> str:
    params = {
        "client_id":     _CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  _REDIRECT_URI,
        "response_mode": "query",
        "scope":         "openid profile email " + " ".join(_SCOPES),
    }
    return f"{_AUTHORITY}/oauth2/v2.0/authorize?" + urlencode(params)


def _exchange_code(code: str) -> dict:
    return _msal_app().acquire_token_by_authorization_code(
        code=code,
        scopes=_SCOPES,
        redirect_uri=_REDIRECT_URI,
    )


def _valid_tenant(result: dict) -> bool:
    tid = result.get("id_token_claims", {}).get("tid", "")
    return tid == _TENANT_ID


def _user_info(result: dict) -> dict:
    claims = result.get("id_token_claims", {})
    return {
        "name":  claims.get("name", "Usuario"),
        "email": claims.get("preferred_username", claims.get("upn", "")),
    }


def _show_login_page(error: str = ""):
    auth_url = _build_auth_url()

    # ── Page config is already set in app.py ──────────────────────────────
    logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "ldh_logo.jpg")

    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown("<div style='height: 60px'></div>", unsafe_allow_html=True)

        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)

        st.markdown(
            """
            <h2 style='text-align:center; color:#003087; margin-top:16px;'>
                Candidates Factory
            </h2>
            <p style='text-align:center; color:#666; font-size:14px; margin-bottom:28px;'>
                LDH Latam Digital Hub by Stefanini
            </p>
            """,
            unsafe_allow_html=True,
        )

        if error:
            st.error(error)

        st.markdown(
            f"""
            <div style='text-align:center; margin-top:8px;'>
                <a href="{auth_url}" target="_self" style="text-decoration:none;">
                    <div style="
                        display:inline-block;
                        background:#003087;
                        color:white;
                        font-family:sans-serif;
                        font-size:15px;
                        font-weight:600;
                        padding:12px 28px;
                        border-radius:6px;
                        cursor:pointer;
                        letter-spacing:0.3px;
                    ">
                        🔐 &nbsp; Iniciar sesión con Microsoft
                    </div>
                </a>
            </div>
            <p style='text-align:center; color:#999; font-size:11px; margin-top:20px;'>
                Solo accesible para usuarios de Stefanini
            </p>
            """,
            unsafe_allow_html=True,
        )


def require_auth() -> dict:
    """
    Call at the top of app.py before any content.
    Returns the authenticated user dict {"name": ..., "email": ...}
    or stops the app and shows the login page.
    """
    # ── Already authenticated ─────────────────────────────────────────────
    if st.session_state.get("_auth_user"):
        return st.session_state["_auth_user"]

    # ── OAuth callback: Microsoft redirected back with ?code= ─────────────
    params = st.query_params
    if "code" in params:
        code = params["code"]
        st.query_params.clear()

        with st.spinner("Verificando credenciales..."):
            result = _exchange_code(code)

        if "error" in result:
            _show_login_page(
                error=f"Error de autenticación: {result.get('error_description', result['error'])}"
            )
            st.stop()

        if not _valid_tenant(result):
            _show_login_page(
                error="Acceso denegado. Solo usuarios de Stefanini pueden acceder."
            )
            st.stop()

        user = _user_info(result)
        st.session_state["_auth_user"] = user
        st.rerun()

    # ── Not authenticated — show login page ───────────────────────────────
    _show_login_page()
    st.stop()


def logout():
    """Call when the user clicks logout."""
    st.session_state.pop("_auth_user", None)
    st.rerun()
