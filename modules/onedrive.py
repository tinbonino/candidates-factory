"""
Uploads files to OneDrive via Microsoft Graph API using MSAL (client credentials flow).
Requires: AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID in .env
"""
import os
import requests
import msal
from dotenv import load_dotenv

load_dotenv()

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPE = ["https://graph.microsoft.com/.default"]


def _get_token() -> str:
    client_id = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    tenant_id = os.getenv("AZURE_TENANT_ID")

    if not all([client_id, client_secret, tenant_id]):
        raise ValueError(
            "OneDrive credentials not configured. "
            "Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID in .env"
        )

    app = msal.ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret,
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in result:
        raise RuntimeError(f"Failed to acquire token: {result.get('error_description')}")
    return result["access_token"]


def _ensure_folder(token: str, folder_path: str) -> str:
    """Creates the folder if it doesn't exist; returns its drive item ID."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Use the /me/drive/root:/{path} endpoint to upsert folder hierarchy
    url = f"{GRAPH_BASE}/me/drive/root:/{folder_path}"
    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        return resp.json()["id"]

    # Folder does not exist — create it
    parts = folder_path.rsplit("/", 1)
    parent_path = parts[0] if len(parts) == 2 else ""
    folder_name = parts[-1]

    if parent_path:
        parent_url = f"{GRAPH_BASE}/me/drive/root:/{parent_path}:/children"
    else:
        parent_url = f"{GRAPH_BASE}/me/drive/root/children"

    body = {
        "name": folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "rename",
    }
    resp = requests.post(parent_url, json=body, headers=headers)
    resp.raise_for_status()
    return resp.json()["id"]


def upload_file(local_path: str, remote_filename: str, candidate_folder: str) -> str:
    """
    Uploads a local file to OneDrive under ONEDRIVE_ROOT_FOLDER/candidate_folder/.
    Returns the web URL of the uploaded file.
    """
    root_folder = os.getenv("ONEDRIVE_ROOT_FOLDER", "Candidates Factory")
    full_path = f"{root_folder}/{candidate_folder}"

    token = _get_token()
    _ensure_folder(token, full_path)

    upload_url = f"{GRAPH_BASE}/me/drive/root:/{full_path}/{remote_filename}:/content"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/pdf",
    }

    with open(local_path, "rb") as f:
        resp = requests.put(upload_url, headers=headers, data=f)
    resp.raise_for_status()

    return resp.json().get("webUrl", "")


def upload_candidate_files(
    candidate_display_name: str,
    infographic_path: str,
    submission_form_path: str,
    branded_resume_path: str,
) -> dict:
    """
    Uploads the three generated PDFs and returns a dict with their OneDrive links.
    """
    folder = candidate_display_name  # e.g. "Juan M."
    return {
        "infographic": upload_file(infographic_path, "infographic.pdf", folder),
        "submission_form": upload_file(submission_form_path, "submission_form.pdf", folder),
        "resume_branded": upload_file(branded_resume_path, "resume_branded.pdf", folder),
    }
