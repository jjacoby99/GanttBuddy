import requests
import streamlit as st
import pydantic
import datetime as dt
from typing import Any, List
from uuid import UUID
from zoneinfo import ZoneInfo
import pandas as pd

from models.delay import Delay, DelayEditorRow  
from models.forecast import ForecastResponse, parse_forecast_response
from typing import Optional

from logic.backend.config import get_backend_environment_config
from logic.backend.export_project import project_to_import_payload

from models.project import Project
from models.crew import CrewOut
from models.delay import DelayType
from models.site import SiteOut
from models.todo import TodoIn, TodoUpsertRow


API_BASE = get_backend_environment_config().api_base_url


@st.cache_data
def get_current_user(auth_headers: dict) -> dict:
    response = requests.get(f"{API_BASE}/auth/me", headers=auth_headers, timeout=10)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to get current user: {response.text}")
    return response.json()

@st.cache_data
def fetch_project_snapshot(project_id: str, headers) -> dict:
    url = f"{API_BASE}/projects/{project_id}/snapshot"

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

@st.cache_data
def fetch_projects(headers, include_closed: bool = False) -> dict:
    url = f"{API_BASE}/projects"
    
    params = {"include_closed": include_closed}
    
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_project_members(*, headers: dict, project_id: str | UUID) -> Any:
    url = f"{API_BASE}/projects/{project_id}/members"
    return _request_json(method="GET", url=url, headers=headers)


@st.cache_data(ttl=30, show_spinner=False)
def fetch_project_delete_impact(*, headers: dict, project_id: str | UUID) -> Any:
    url = f"{API_BASE}/projects/{project_id}/delete-impact"
    return _request_json(method="GET", url=url, headers=headers)


def upsert_project_member(
    *,
    headers: dict,
    project_id: str | UUID,
    user_id: str | UUID,
    role: str,
) -> dict:
    url = f"{API_BASE}/projects/{project_id}/members/{user_id}"
    response = requests.put(url, headers=headers, json={"role": role}, timeout=30)
    try:
        response.raise_for_status()
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to update project member: {e} {body}")
    fetch_project_members.clear()
    return response.json()


def delete_project_member(
    *,
    headers: dict,
    project_id: str | UUID,
    user_id: str | UUID,
) -> None:
    url = f"{API_BASE}/projects/{project_id}/members/{user_id}"
    response = requests.delete(url, headers=headers, timeout=30)
    try:
        response.raise_for_status()
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to delete project member: {e} {body}")
    fetch_project_members.clear()


def delete_project(
    *,
    headers: dict,
    project_id: str | UUID,
    delete_todos: bool,
) -> None:
    url = f"{API_BASE}/projects/{project_id}"
    response = requests.delete(
        url,
        headers=headers,
        json={"delete_todos": delete_todos},
        timeout=30,
    )
    try:
        response.raise_for_status()
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to delete project: {e} {body}")

    fetch_project_delete_impact.clear()
    fetch_project_members.clear()
    fetch_project_snapshot.clear()
    fetch_projects.clear()

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


def add_site(headers: dict, site: SiteOut) -> dict:
    url = f"{API_BASE}/sites"

    try:
        response = requests.post(url, json=site.model_dump(mode="json"), headers=headers, timeout=30)
        response.raise_for_status()
        fetch_sites.clear()
        return response.json()
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to create site: {e} {body}")
    

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


def headers_for_organization(headers: dict | None, organization_id: str | UUID | None) -> dict:
    scoped_headers = dict(headers or {})
    if organization_id:
        scoped_headers["X-Organization-Id"] = str(organization_id)
    return scoped_headers


def _request_json(
    *,
    method: str,
    url: str,
    headers: dict,
    params: dict[str, Any] | None = None,
    timeout: int = 30,
) -> Any:
    response = requests.request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        timeout=timeout,
    )
    try:
        response.raise_for_status()
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Request failed for {url}: {e} {body}")
    return response.json()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_organization_dashboard(
    *,
    headers: dict,
    organization_id: str | UUID,
) -> dict:
    url = f"{API_BASE}/organizations/{organization_id}/dashboard"
    return _request_json(method="GET", url=url, headers=headers)


@st.cache_data(ttl=30, show_spinner=False)
def fetch_organization_projects_summary(
    *,
    headers: dict,
    organization_id: str | UUID,
    status: str = "all",
    sort: str = "last_activity_at",
    page: int = 1,
    page_size: int = 100,
) -> dict:
    url = f"{API_BASE}/organizations/{organization_id}/projects/summary"
    params = {
        "status": status,
        "sort": sort,
        "page": page,
        "page_size": page_size,
    }
    return _request_json(method="GET", url=url, headers=headers, params=params)


@st.cache_data(ttl=30, show_spinner=False)
def fetch_organization_users_summary(
    *,
    headers: dict,
    organization_id: str | UUID,
    status: str = "all",
    role: str | None = None,
    sort: str = "last_login_at",
    page: int = 1,
    page_size: int = 100,
) -> dict:
    url = f"{API_BASE}/organizations/{organization_id}/users/summary"
    params: dict[str, Any] = {
        "status": status,
        "sort": sort,
        "page": page,
        "page_size": page_size,
    }
    if role:
        params["role"] = role
    return _request_json(method="GET", url=url, headers=headers, params=params)


@st.cache_data(ttl=30, show_spinner=False)
def fetch_organization_user_detail(
    *,
    headers: dict,
    organization_id: str | UUID,
    user_id: str | UUID,
) -> dict:
    url = f"{API_BASE}/organizations/{organization_id}/users/{user_id}"
    return _request_json(method="GET", url=url, headers=headers)


@st.cache_data(ttl=30, show_spinner=False)
def fetch_organization_activity(
    *,
    headers: dict,
    organization_id: str | UUID,
    event_type: str | None = None,
    actor_user_id: str | UUID | None = None,
    project_id: str | UUID | None = None,
    limit: int = 25,
) -> dict:
    url = f"{API_BASE}/organizations/{organization_id}/activity"
    params: dict[str, Any] = {"limit": limit}
    if event_type:
        params["event_type"] = event_type
    if actor_user_id:
        params["actor_user_id"] = str(actor_user_id)
    if project_id:
        params["project_id"] = str(project_id)
    return _request_json(method="GET", url=url, headers=headers, params=params)


def update_organization_user_role(
    *,
    headers: dict,
    organization_id: str | UUID,
    user_id: str | UUID,
    role: str,
) -> dict:
    url = f"{API_BASE}/organizations/{organization_id}/users/{user_id}/role"
    response = requests.patch(url, headers=headers, json={"role": role}, timeout=30)
    try:
        response.raise_for_status()
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to update organization role: {e} {body}")
    return response.json()


@st.cache_data
def fetch_project_forecast(headers: dict, project_id: str) -> ForecastResponse:
    url = f"{API_BASE}/projects/{project_id}/analytics/forecast"

    try:
        response = requests.get(url=url, headers=headers, timeout=30)
        response.raise_for_status()
        return parse_forecast_response(response.json())
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass
        raise ValueError(f"Failed to fetch forecast for {project_id}: {e} {body}")
    

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

def closeout_project(
        *,
        headers: dict,
        project_id: str | UUID,
):
    project_id = str(project_id)
    url = f"{API_BASE}/projects/closeout/{project_id}"

    try:
        response = requests.patch(url=url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()    
    except Exception as e:
        body = ""
        try:
            body = response.text
        except Exception:
            pass

        raise ValueError(f"Failed to closeout project {project_id}. This either means the project doesn't exist or its already closed.")


from models.task import TaskStatus

def fetch_todos(
        *,
        headers: dict,
        project_id: Optional[str | UUID] = None,
        task_id: Optional[str | UUID] = None,
        status: Optional[str | TaskStatus] = None
):
    params = {}
    if project_id:
        params["project_id"] = str(project_id)
    
    if task_id:
        params["task_id"] = str(task_id)
    
    if status:
        status_str = status.value if isinstance(status, TaskStatus) else status
        params["status"] = status_str
    
    url = f"{API_BASE}/todos"

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        body = ""
        try:
            body = resp.text
        except Exception:
            pass
        
        parts = [f"Failed to fetch todos"]
        if project_id:
            parts.append(f"for project id: {project_id}")
        if task_id:
            parts.append(f"for task id: {task_id}")
        if status:
            parts.append(f"with status {status_str}")

        message = "\n\t".join(parts)

        raise ValueError(f"Error fetching todos: {body}.\n{message}")


def save_todos(
    *,
    headers: dict,
    rows: list[TodoUpsertRow],
    project_id: str | UUID | None = None,
    replace: bool = False,
) -> list[TodoIn]:
    params: dict[str, str] = {}
    if project_id is not None:
        params["project_id"] = str(project_id)
    if replace:
        params["replace"] = "true"

    payload: list[dict] = []
    for row in rows:
        item = row.model_dump()
        for field in ("id", "project_id", "task_id"):
            if item.get(field):
                item[field] = str(item[field])
            else:
                item[field] = None
        for field in ("start_date", "due_date", "completed_at"):
            item[field] = _to_utc_iso(item.get(field))
        payload.append(item)

    url = f"{API_BASE}/todos"
    resp = requests.put(url, headers=headers, json=payload, params=params or None, timeout=30)
    resp.raise_for_status()
    return [TodoIn.model_validate(item) for item in resp.json()]


def delete_todo(
    *,
    headers: dict,
    todo_id: str | UUID,
) -> None:
    url = f"{API_BASE}/todos/{todo_id}"
    resp = requests.delete(url, headers=headers, timeout=30)
    resp.raise_for_status()
