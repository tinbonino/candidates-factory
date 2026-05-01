"""
Uploads files to a SharePoint document library via Microsoft Graph API.
Uses MSAL client credentials flow (app-only auth).

Required env vars:
    AZURE_CLIENT_ID
    AZURE_CLIENT_SECRET
    AZURE_TENANT_ID
    SHAREPOINT_SITE_URL   e.g. https://stefaninilatam.sharepoint.com/sites/LDHTalentTeam
    ONEDRIVE_ROOT_FOLDER  folder name inside Documents (default: Candidates Factory)
"""
import os
from urllib.parse import urlparse

import msal
import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPE      = ["https://graph.microsoft.com/.default"]


# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_token() -> str:
    client_id     = os.getenv("AZURE_CLIENT_ID")
    client_secret = os.getenv("AZURE_CLIENT_SECRET")
    tenant_id     = os.getenv("AZURE_TENANT_ID")

    if not all([client_id, client_secret, tenant_id]):
        raise ValueError(
            "Azure credentials not configured. "
            "Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET and AZURE_TENANT_ID in .env"
        )

    app = msal.ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret,
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in result:
        raise RuntimeError(
            f"Failed to acquire token: {result.get('error_description', result)}"
        )
    return result["access_token"]


# ── SharePoint site resolution ────────────────────────────────────────────────

def _get_site_id(token: str) -> str:
    """
    Resolves the SharePoint site URL to its Graph site ID.
    e.g. https://stefaninilatam.sharepoint.com/sites/LDHTalentTeam
         → stefaninilatam.sharepoint.com,<site-guid>,<web-guid>
    """
    site_url = os.getenv("SHAREPOINT_SITE_URL", "").rstrip("/")
    if not site_url:
        raise ValueError("SHAREPOINT_SITE_URL is not set in .env")

    parsed    = urlparse(site_url)
    hostname  = parsed.netloc   # stefaninilatam.sharepoint.com
    site_path = parsed.path     # /sites/LDHTalentTeam

    url     = f"{GRAPH_BASE}/sites/{hostname}:{site_path}"
    headers = {"Authorization": f"Bearer {token}"}
    resp    = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["id"]


# ── Folder management ─────────────────────────────────────────────────────────

def _ensure_folder(token: str, site_id: str, folder_path: str) -> str:
    """
    Ensures every level of folder_path exists in the site's default document library.
    Creates missing levels one by one.
    Returns the item ID of the deepest folder.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }

    # Fast path — folder already exists
    resp = requests.get(
        f"{GRAPH_BASE}/sites/{site_id}/drive/root:/{folder_path}",
        headers=headers,
        timeout=30,
    )
    if resp.status_code == 200:
        return resp.json()["id"]

    # Walk path levels and create any that are missing
    parts        = [p for p in folder_path.split("/") if p]
    current_path = ""
    folder_id    = None

    for part in parts:
        current_path = f"{current_path}/{part}" if current_path else part

        check = requests.get(
            f"{GRAPH_BASE}/sites/{site_id}/drive/root:/{current_path}",
            headers=headers,
            timeout=30,
        )
        if check.status_code == 200:
            folder_id = check.json()["id"]
            continue

        # Level doesn't exist — create it
        parent_path  = "/".join(current_path.split("/")[:-1])
        if parent_path:
            create_url = f"{GRAPH_BASE}/sites/{site_id}/drive/root:/{parent_path}:/children"
        else:
            create_url = f"{GRAPH_BASE}/sites/{site_id}/drive/root/children"

        body = {
            "name":   part,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "ignore",
        }
        cr = requests.post(create_url, json=body, headers=headers, timeout=30)

        if cr.status_code == 409:
            # Already exists — fetch it
            existing = requests.get(
                f"{GRAPH_BASE}/sites/{site_id}/drive/root:/{current_path}",
                headers=headers,
                timeout=30,
            )
            existing.raise_for_status()
            folder_id = existing.json()["id"]
        else:
            cr.raise_for_status()
            folder_id = cr.json()["id"]

    return folder_id


# ── Upload ────────────────────────────────────────────────────────────────────

def _upload_bytes(
    token: str,
    site_id: str,
    full_folder_path: str,
    filename: str,
    data: bytes,
) -> str:
    """PUT file bytes into the SharePoint document library. Returns the webUrl."""
    upload_url = (
        f"{GRAPH_BASE}/sites/{site_id}/drive"
        f"/root:/{full_folder_path}/{filename}:/content"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/pdf",
    }
    resp = requests.put(upload_url, headers=headers, data=data, timeout=60)
    resp.raise_for_status()
    return resp.json().get("webUrl", "")


# ── Public API ────────────────────────────────────────────────────────────────

def upload_candidate_files(candidate_display_name: str, pdf_bytes: dict) -> dict:
    """
    Uploads the three generated PDFs (as bytes) to SharePoint.

    Args:
        candidate_display_name: e.g. "Juan M."
        pdf_bytes: {
            "infographic":     bytes,
            "submission_form": bytes,
            "resume_branded":  bytes,
        }

    Returns:
        {
            "infographic":     "<webUrl>",
            "submission_form": "<webUrl>",
            "resume_branded":  "<webUrl>",
        }
    """
    root_folder = os.getenv("ONEDRIVE_ROOT_FOLDER", "Candidates Factory")
    folder_path = f"{root_folder}/{candidate_display_name}"
    safe        = candidate_display_name.replace(" ", "_")

    token   = _get_token()
    site_id = _get_site_id(token)
    _ensure_folder(token, site_id, folder_path)

    return {
        "infographic":    _upload_bytes(token, site_id, folder_path, f"infographic_{safe}.pdf",    pdf_bytes["infographic"]),
        "submission_form": _upload_bytes(token, site_id, folder_path, f"submission_form_{safe}.pdf", pdf_bytes["submission_form"]),
        "resume_branded": _upload_bytes(token, site_id, folder_path, f"resume_branded_{safe}.pdf",  pdf_bytes["resume_branded"]),
    }
