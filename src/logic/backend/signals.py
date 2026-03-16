from __future__ import annotations

import datetime as dt
from json import JSONDecodeError
from typing import Any, Optional
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

from logic.backend.api_client import API_BASE
from models.signals import (
    DataSource,
    DataSourceType,
    IngestionRun,
    SignalDataType,
    SignalDefinition,
    SignalInterval,
    SignalObservation,
    parse_data_sources,
    parse_ingestion_runs,
    parse_intervals,
    parse_observations,
    parse_signal_definitions,
)


def _request_json(
    *,
    method: str,
    path: str,
    headers: dict,
    params: Optional[dict[str, Any]] = None,
    json: Optional[dict[str, Any]] = None,
) -> Any:
    response: requests.Response | None = None
    try:
        response = requests.request(
            method=method,
            url=f"{API_BASE}{path}",
            headers=headers,
            params=params,
            json=json,
            timeout=30,
        )
        response.raise_for_status()
        if not response.content:
            return None
        return response.json()
    except requests.RequestException as exc:
        body = ""
        if response is not None:
            try:
                body = response.text
            except Exception:
                body = ""
        raise ValueError(f"{method} {path} failed: {exc} {body}".strip()) from exc
    except JSONDecodeError as exc:
        raise ValueError(f"{method} {path} returned invalid JSON.") from exc


def _to_utc_iso(value: dt.datetime | None, timezone: ZoneInfo) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone)
    return value.astimezone(dt.UTC).isoformat().replace("+00:00", "Z")


@st.cache_data(show_spinner=False)
def fetch_signal_definitions(
    headers: dict,
    project_id: str,
    data_type: SignalDataType | None = None,
    data_source_id: str | None = None,
) -> list[SignalDefinition]:
    params: dict[str, Any] = {}
    if data_type:
        params["data_type"] = data_type.value
    if data_source_id:
        params["data_source_id"] = data_source_id
    payload = _request_json(
        method="GET",
        path=f"/projects/{project_id}/signals",
        headers=headers,
        params=params or None,
    )
    return parse_signal_definitions(payload)


@st.cache_data(show_spinner=False)
def fetch_signal_definition(headers: dict, project_id: str, signal_id: str) -> SignalDefinition:
    payload = _request_json(
        method="GET",
        path=f"/projects/{project_id}/signals/{signal_id}",
        headers=headers,
    )
    return SignalDefinition.model_validate(payload)


def create_signal_definition(headers: dict, project_id: str, payload: dict[str, Any]) -> SignalDefinition:
    data = _request_json(
        method="POST",
        path=f"/projects/{project_id}/signals",
        headers=headers,
        json=payload,
    )
    clear_signal_caches()
    return SignalDefinition.model_validate(data)


def update_signal_definition(headers: dict, project_id: str, signal_id: str, payload: dict[str, Any]) -> SignalDefinition:
    data = _request_json(
        method="PATCH",
        path=f"/projects/{project_id}/signals/{signal_id}",
        headers=headers,
        json=payload,
    )
    clear_signal_caches()
    return SignalDefinition.model_validate(data)


def delete_signal_definition(headers: dict, project_id: str, signal_id: str) -> None:
    _request_json(
        method="DELETE",
        path=f"/projects/{project_id}/signals/{signal_id}",
        headers=headers,
    )
    clear_signal_caches()


@st.cache_data(show_spinner=False)
def fetch_data_sources(
    headers: dict,
    project_id: str,
    source_type: DataSourceType | None = None,
    is_active: bool | None = None,
) -> list[DataSource]:
    params: dict[str, Any] = {}
    if source_type:
        params["source_type"] = source_type.value
    if is_active is not None:
        params["is_active"] = str(is_active).lower()
    payload = _request_json(
        method="GET",
        path=f"/projects/{project_id}/data-sources",
        headers=headers,
        params=params or None,
    )
    return parse_data_sources(payload)


@st.cache_data(show_spinner=False)
def fetch_data_source(headers: dict, project_id: str, data_source_id: str) -> DataSource:
    payload = _request_json(
        method="GET",
        path=f"/projects/{project_id}/data-sources/{data_source_id}",
        headers=headers,
    )
    return DataSource.model_validate(payload)


def create_data_source(headers: dict, project_id: str, payload: dict[str, Any]) -> DataSource:
    data = _request_json(
        method="POST",
        path=f"/projects/{project_id}/data-sources",
        headers=headers,
        json=payload,
    )
    clear_signal_caches()
    return DataSource.model_validate(data)


def update_data_source(headers: dict, project_id: str, data_source_id: str, payload: dict[str, Any]) -> DataSource:
    data = _request_json(
        method="PATCH",
        path=f"/projects/{project_id}/data-sources/{data_source_id}",
        headers=headers,
        json=payload,
    )
    clear_signal_caches()
    return DataSource.model_validate(data)


def delete_data_source(headers: dict, project_id: str, data_source_id: str) -> None:
    _request_json(
        method="DELETE",
        path=f"/projects/{project_id}/data-sources/{data_source_id}",
        headers=headers,
    )
    clear_signal_caches()


def test_data_source(headers: dict, project_id: str, data_source_id: str) -> dict[str, Any] | None:
    result = _request_json(
        method="POST",
        path=f"/projects/{project_id}/data-sources/{data_source_id}/test",
        headers=headers,
    )
    clear_signal_caches()
    return result


def create_signal_observations(
    headers: dict,
    project_id: str,
    signal_id: str,
    observations: list[dict[str, Any]],
) -> list[SignalObservation]:
    payload = _request_json(
        method="POST",
        path=f"/projects/{project_id}/signals/{signal_id}/observations",
        headers=headers,
        json={"observations": observations},
    )
    clear_signal_caches()
    return parse_observations(payload)


@st.cache_data(show_spinner=False)
def fetch_signal_observations(
    headers: dict,
    project_id: str,
    signal_id: str,
    start: dt.datetime | None = None,
    end: dt.datetime | None = None,
    limit: int = 500,
    offset: int = 0,
) -> list[SignalObservation]:
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if start:
        params["start"] = start.isoformat().replace("+00:00", "Z")
    if end:
        params["end"] = end.isoformat().replace("+00:00", "Z")
    payload = _request_json(
        method="GET",
        path=f"/projects/{project_id}/signals/{signal_id}/observations",
        headers=headers,
        params=params,
    )
    return parse_observations(payload)


def delete_signal_observations(
    headers: dict,
    project_id: str,
    signal_id: str,
    start: dt.datetime | None = None,
    end: dt.datetime | None = None,
    ingestion_run_id: str | None = None,
) -> None:
    payload: dict[str, Any] = {}
    if start:
        payload["start"] = start.isoformat().replace("+00:00", "Z")
    if end:
        payload["end"] = end.isoformat().replace("+00:00", "Z")
    if ingestion_run_id:
        payload["ingestion_run_id"] = ingestion_run_id
    _request_json(
        method="DELETE",
        path=f"/projects/{project_id}/signals/{signal_id}/observations",
        headers=headers,
        json=payload,
    )
    clear_signal_caches()


@st.cache_data(show_spinner=False)
def fetch_signal_intervals(
    headers: dict,
    project_id: str,
    signal_id: str,
    start: dt.datetime | None = None,
    end: dt.datetime | None = None,
) -> list[SignalInterval]:
    params: dict[str, Any] = {}
    if start:
        params["start"] = start.isoformat().replace("+00:00", "Z")
    if end:
        params["end"] = end.isoformat().replace("+00:00", "Z")
    payload = _request_json(
        method="GET",
        path=f"/projects/{project_id}/signals/{signal_id}/intervals",
        headers=headers,
        params=params or None,
    )
    return parse_intervals(payload)


def trigger_manual_ingestion(
    headers: dict,
    project_id: str,
    data_source_id: str,
    payload: dict[str, Any],
) -> IngestionRun:
    data = _request_json(
        method="POST",
        path=f"/projects/{project_id}/data-sources/{data_source_id}/ingestions",
        headers=headers,
        json=payload,
    )
    clear_signal_caches()
    return IngestionRun.model_validate(data)


@st.cache_data(show_spinner=False)
def fetch_ingestion_runs(headers: dict, project_id: str, data_source_id: str) -> list[IngestionRun]:
    payload = _request_json(
        method="GET",
        path=f"/projects/{project_id}/data-sources/{data_source_id}/ingestions",
        headers=headers,
    )
    return parse_ingestion_runs(payload)


@st.cache_data(show_spinner=False)
def fetch_ingestion_run(headers: dict, project_id: str, ingestion_run_id: str) -> IngestionRun:
    payload = _request_json(
        method="GET",
        path=f"/projects/{project_id}/ingestions/{ingestion_run_id}",
        headers=headers,
    )
    return IngestionRun.model_validate(payload)


def rollback_ingestion_run(headers: dict, project_id: str, ingestion_run_id: str) -> dict[str, Any] | None:
    result = _request_json(
        method="POST",
        path=f"/projects/{project_id}/ingestions/{ingestion_run_id}/rollback",
        headers=headers,
    )
    clear_signal_caches()
    return result


def clear_signal_caches() -> None:
    fetch_signal_definitions.clear()
    fetch_signal_definition.clear()
    fetch_data_sources.clear()
    fetch_data_source.clear()
    fetch_signal_observations.clear()
    fetch_signal_intervals.clear()
    fetch_ingestion_runs.clear()
    fetch_ingestion_run.clear()


def observations_to_frame(
    observations: list[SignalObservation],
    *,
    timezone: ZoneInfo,
    data_type: SignalDataType,
) -> pd.DataFrame:
    df = SignalObservation.to_frame(observations)
    if df.empty:
        return df
    df["timestamp_local"] = pd.to_datetime(df["timestamp_utc"], utc=True).dt.tz_convert(timezone)
    if data_type == SignalDataType.BOOLEAN:
        df["value_label"] = df["value"].map(lambda value: "True" if value is True else "False")
    else:
        df["value_label"] = df["value"].astype(str)
    return df.sort_values("timestamp_local")


def intervals_to_frame(intervals: list[SignalInterval], *, timezone: ZoneInfo) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in intervals:
        raw = item.model_dump()
        start = raw.get("start_utc") or raw.get("start") or raw.get("started_at")
        end = raw.get("end_utc") or raw.get("end") or raw.get("ended_at")
        value = raw.get("value")
        label = raw.get("label")
        duration_seconds = raw.get("duration_seconds")
        if duration_seconds is None and start and end:
            duration_seconds = (end - start).total_seconds()
        rows.append(
            {
                "start_local": start.astimezone(timezone) if start else None,
                "end_local": end.astimezone(timezone) if end else None,
                "value": value if value is not None else label,
                "duration_minutes": round(duration_seconds / 60, 2) if duration_seconds is not None else None,
            }
        )
    return pd.DataFrame(rows)


def as_project_utc_window(
    start_local: dt.datetime | None,
    end_local: dt.datetime | None,
    *,
    timezone: ZoneInfo,
) -> tuple[dt.datetime | None, dt.datetime | None]:
    start_utc = None
    end_utc = None
    if start_local:
        start_utc = dt.datetime.fromisoformat(_to_utc_iso(start_local, timezone).replace("Z", "+00:00"))
    if end_local:
        end_utc = dt.datetime.fromisoformat(_to_utc_iso(end_local, timezone).replace("Z", "+00:00"))
    return start_utc, end_utc
