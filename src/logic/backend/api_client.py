import requests
import streamlit as st
import pydantic
import datetime as dt
from typing import List
from uuid import UUID
from zoneinfo import ZoneInfo
import pandas as pd

from models.delay import Delay, DelayEditorRow  
from typing import Optional

from logic.backend.export_project import project_to_import_payload

from models.project import Project
from models.crew import CrewOut
from models.delay import DelayType


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
        return response.json()
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
    

def fetch_delays(
        headers: dict,
        project_id: str,
        delay_type: Optional[DelayType] = None,
        shift_assignment_id: Optional[str] = None,
        time_min: Optional[dt.datetime] = None,
        time_max: Optional[dt.datetime] = None,
        limit: Optional[int] = 200,
):
    params = {"project_id": project_id}
    if time_min:
        params["time_min"] = time_min.isoformat()
    if time_max:
        params["time_max"] = time_max.isoformat()
    if delay_type:
        params["delay_type"] = delay_type.value
    if shift_assignment_id:
        params["shift_assignment_id"] = shift_assignment_id
    if limit:
        params["limit"] = limit


    url = f"{API_BASE}/delays"
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to fetch delays for {project_id}: {e} {body}")
    

LOCAL_TZ = ZoneInfo("America/Vancouver")


def _to_utc_iso(x):
    """Convert pandas/py datetimes to UTC ISO8601 string with Z; keep None as None."""
    if x is None:
        return None

    # pandas Timestamp -> python datetime
    if isinstance(x, pd.Timestamp):
        x = x.to_pydatetime()

    if not isinstance(x, dt.datetime):
        return x  # leave non-datetime types alone

    # If Streamlit returns naive local time, interpret as LOCAL_TZ
    if x.tzinfo is None:
        x = x.replace(tzinfo=LOCAL_TZ)

    x_utc = x.astimezone(dt.UTC)
    # Use Z suffix
    return x_utc.isoformat().replace("+00:00", "Z")


def save_delays(
    *,
    headers: dict,
    project_id: str | UUID,
    edited_rows: List[DelayEditorRow],
    replace: bool = False,
) -> list[Delay]:
    pid = str(project_id)

    payload = []
    for r in edited_rows:
        d = r.model_dump()  # python objects
        
        # normalize id
        if not d.get("id"):
            d["id"] = None

        # normalize datetimes -> UTC ISO strings
        d["start_dt"] = _to_utc_iso(d.get("start_dt"))
        d["end_dt"] = _to_utc_iso(d.get("end_dt"))

        payload.append(d)

    url = f"{API_BASE}/delays/{pid}/delays"
    params = {"replace": "true"} if replace else None
    resp = requests.put(url, headers=headers, json=payload, params=params, timeout=30)
    resp.raise_for_status()

    return [Delay.model_validate(x) for x in resp.json()]


def fetch_events(
        *,
        headers: dict,
        project_id: Optional[str | UUID] = None,
        from_dt: Optional[dt.datetime] = None,
        n_events: Optional[int] = 10
):
    params = {}
    if project_id:
        params["project_id"] = str(project_id)
    if from_dt:
        params["from_dt"] = from_dt.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")
    if n_events:
        params["n_events"] = n_events

    url = f"{API_BASE}/events"

    try:
        resp = requests.get(url=url, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        body = ""
        try:
            body = resp.text
        except Exception:
            pass
        raise ValueError(f"Failed to fetch events for: {e} {body}")
