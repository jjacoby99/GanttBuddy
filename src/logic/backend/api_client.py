import requests
import streamlit as st
import pydantic
import datetime as dt

from typing import Optional

from logic.backend.export_project import project_to_import_payload

from models.project import Project
from models.crew import CrewOut

API_BASE = "http://127.0.0.1:8000"  # change for deployed

@st.cache_data
def fetch_project_snapshot(project_id: str, headers) -> dict:
    url = f"{API_BASE}/projects/{project_id}/snapshot"

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

@st.cache_data
def fetch_projects(headers) -> dict:
    url = f"{API_BASE}/projects"

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def save_project(project: Project, headers) -> str:
    metadata = st.session_state.get("reline_metadata", None)
    payload = project_to_import_payload(project, metadata=metadata)

    try:
        response = requests.post(f"{API_BASE}/projects/import", json=payload, headers=headers)
        response.raise_for_status()
        return response.json().get("project_id")
    except requests.RequestException as e:

        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to save project: {e} {body}")
    
@st.cache_data
def fetch_attention_tasks(headers: dict) -> dict:
    url = f"{API_BASE}/projects/attention"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise ValueError(f"Failed to fetch attention tasks: {e} {response.text}")


@st.cache_data
def fetch_sites(headers: dict) -> dict:
    url = f"{API_BASE}/sites"
    try:
        response = requests.get(url, headers=headers,timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise ValueError(f"Failed to fetch sites: {e} {response.text}")
    

@st.cache_data
def fetch_mills(headers: dict, site_id: str | None = None, active: bool | None = True) -> dict:
    """
    Fetch mills for dropdown hydration.

    Args:
        headers: auth headers (Bearer token etc.)
        site_id: optional UUID string to filter mills by site
        active: True/False to filter by active, or None for all

    Returns:
        JSON response (list of mills) as python object.
    """
    url = f"{API_BASE}/mills"
    params: dict[str, str] = {}

    if site_id:
        params["site_id"] = site_id
    if active is not None:
        # backend expects bool; requests will serialize as 'True'/'False'
        # FastAPI will parse it fine.
        params["active"] = str(active).lower()  # "true"/"false" is safest

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # keep your existing error style
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to fetch mills: {e} {body}")

@st.cache_data
def fetch_site(headers: dict, site_id: str) -> dict:
    url = f"{API_BASE}/sites/{site_id}"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        # keep your existing error style
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to fetch site: {e} {body}")
    

@st.cache_data
def fetch_crews(headers: dict, site_id: str) -> dict:
    url = f"{API_BASE}/crews"
    params = {}
    params["site_id"] = site_id
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to fetch crews: {e} {body}")

def post_new_crew(headers: dict, crew: CrewOut) -> dict:
    url = f"{API_BASE}/crews"

    try:
        response = requests.post(url, json=crew.model_dump(mode="json"), headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to post new crew: {e} {body}")
    

@st.cache_data
def fetch_analytics(headers: dict, project_id: str, date_from: Optional[dt.date], date_to: Optional[dt.date]):
    url = f"{API_BASE}/projects/{project_id}/analytics/dashboard"
    params = {}
    if date_from:
        params["date_from"] = date_from.isoformat()
    if date_to:
        params["date_to"] = date_to.isoformat()
    
    try:
        response = requests.get(url=url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to fetch analytics for {project_id}: {e} {body}")
    
def fetch_inching_performance(
    *,
    headers: dict,
    project_id: str,
    date_from=None,
    date_to=None,
):
    params = {"project_id": project_id}
    if date_from:
        params["date_from"] = date_from.isoformat()
    if date_to:
        params["date_to"] = date_to.isoformat()

    # Adjust base_url / request helper to match how fetch_analytics is implemented in your codebase.
    url = f"{API_BASE}/projects/{project_id}/analytics/inching-performance"

    try:
        response = requests.get(url=url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to fetch analytics for {project_id}: {e} {body}")