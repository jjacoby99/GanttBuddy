import requests
import streamlit as st

from logic.backend.export_project import project_to_import_payload

from models.project import Project

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
    payload = project_to_import_payload(project)

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