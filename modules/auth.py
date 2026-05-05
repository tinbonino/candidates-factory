"""
Username/password authentication using streamlit-authenticator 0.4.x.
Credentials are stored in Streamlit Secrets — never in the repo.

── Streamlit Cloud Secrets format ──────────────────────────────────────────
[auth]
cookie_name   = "ldh_cf_auth"
cookie_key    = "replace_with_a_long_random_string_min_32_chars"
cookie_expiry = 30

[auth.credentials.usernames.mbonino]
name     = "Martin Bonino"
password = "the_plain_text_password"   # hashed automatically on first login

[auth.credentials.usernames.otheruser]
name     = "Other User"
password = "their_password"
────────────────────────────────────────────────────────────────────────────
"""
import streamlit as st
import streamlit_authenticator as stauth


def _build_authenticator() -> stauth.Authenticate:
    sec = st.secrets.get("auth", {})

    credentials: dict = {"usernames": {}}
    for username, info in sec.get("credentials", {}).get("usernames", {}).items():
        credentials["usernames"][username] = {
            "name":     info.get("name", username),
            "password": info.get("password", ""),
        }

    return stauth.Authenticate(
        credentials=credentials,
        cookie_name=sec.get("cookie_name",   "ldh_cf_auth"),
        cookie_key=sec.get("cookie_key",    "change_me_long_random_string"),
        cookie_expiry_days=int(sec.get("cookie_expiry", 30)),
        auto_hash=True,
    )


def require_auth() -> dict:
    """
    Call at the very top of app.py before any content.
    Shows the login form if needed and stops execution until authenticated.
    Returns {"name": "Full Name"} when the user is logged in.
    """
    auth = _build_authenticator()

    auth.login(
        location="main",
        fields={
            "Form name": "Candidates Factory — LDH",
            "Username":  "Usuario",
            "Password":  "Contraseña",
            "Login":     "Ingresar",
        },
    )

    status = st.session_state.get("authentication_status")

    if status is False:
        st.error("❌ Usuario o contraseña incorrectos.")
        st.stop()

    if status is None:
        st.stop()

    # Authenticated ✅
    return {"name": st.session_state.get("name", "Usuario")}


def logout():
    """
    Logs the user out and reruns the app.
    Call when the user clicks the logout button.
    """
    auth = _build_authenticator()
    auth.logout(location="unrendered")
    st.rerun()
