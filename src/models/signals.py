from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class SignalDataType(str, Enum):
    BOOLEAN = "BOOLEAN"
    NUMERIC = "NUMERIC"
    CATEGORICAL = "CATEGORICAL"


class SignalValueMode(str, Enum):
    SAMPLE = "SAMPLE"
    EVENT = "EVENT"
    STATE_CHANGE = "STATE_CHANGE"


class DataSourceType(str, Enum):
    CSV = "CSV"
    EXCEL = "EXCEL"
    API = "API"
    MANUAL = "MANUAL"
    COMPUTED = "COMPUTED"


class IngestionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class SignalBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class SignalDefinition(SignalBaseModel):
    id: str
    project_id: str
    key: str
    name: str
    description: Optional[str] = None
    data_type: SignalDataType
    value_mode: SignalValueMode
    unit: Optional[str] = None
    data_source_id: Optional[str] = None
    is_builtin: bool = False
    metadata_json: dict[str, Any] | None = None
    created_at: Optional[dt.datetime] = None
    updated_at: Optional[dt.datetime] = None

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.key})"

    @staticmethod
    def to_frame(items: list["SignalDefinition"]) -> pd.DataFrame:
        if not items:
            return pd.DataFrame(
                columns=["name", "key", "data_type", "value_mode", "unit", "data_source_id", "is_builtin"]
            )
        return pd.DataFrame(
            [
                {
                    "id": item.id,
                    "name": item.name,
                    "key": item.key,
                    "data_type": item.data_type.value,
                    "value_mode": item.value_mode.value,
                    "unit": item.unit or "",
                    "data_source_id": item.data_source_id or "",
                    "is_builtin": item.is_builtin,
                    "description": item.description or "",
                }
                for item in items
            ]
        )


class DataSource(SignalBaseModel):
    id: str
    project_id: str
    name: str
    source_type: DataSourceType
    config_json: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    last_synced_at: Optional[dt.datetime] = None
    created_at: Optional[dt.datetime] = None
    updated_at: Optional[dt.datetime] = None

    @property
    def display_name(self) -> str:
        return f"{self.name} [{self.source_type.value}]"

    @staticmethod
    def to_frame(items: list["DataSource"]) -> pd.DataFrame:
        if not items:
            return pd.DataFrame(columns=["name", "source_type", "is_active", "last_synced_at"])
        return pd.DataFrame(
            [
                {
                    "id": item.id,
                    "name": item.name,
                    "source_type": item.source_type.value,
                    "is_active": item.is_active,
                    "last_synced_at": item.last_synced_at,
                }
                for item in items
            ]
        )


class SignalObservation(SignalBaseModel):
    id: Optional[str] = None
    signal_id: str
    timestamp_utc: dt.datetime
    numeric_value: Optional[float] = None
    boolean_value: Optional[bool] = None
    text_value: Optional[str] = None
    quality_code: Optional[str] = None
    source_record_key: Optional[str] = None
    ingestion_run_id: Optional[str] = None
    created_at: Optional[dt.datetime] = None

    @property
    def value(self) -> Any:
        if self.numeric_value is not None:
            return self.numeric_value
        if self.boolean_value is not None:
            return self.boolean_value
        return self.text_value

    @staticmethod
    def to_frame(items: list["SignalObservation"]) -> pd.DataFrame:
        if not items:
            return pd.DataFrame(columns=["timestamp_utc", "value", "quality_code", "source_record_key"])
        return pd.DataFrame(
            [
                {
                    "id": item.id,
                    "timestamp_utc": item.timestamp_utc,
                    "value": item.value,
                    "quality_code": item.quality_code or "",
                    "source_record_key": item.source_record_key or "",
                    "ingestion_run_id": item.ingestion_run_id or "",
                }
                for item in items
            ]
        )


class SignalInterval(SignalBaseModel):
    start_utc: Optional[dt.datetime] = None
    end_utc: Optional[dt.datetime] = None
    value: Any = None
    label: Optional[str] = None
    duration_seconds: Optional[float] = None


class IngestionRun(SignalBaseModel):
    id: str
    data_source_id: str
    status: IngestionStatus
    started_at: Optional[dt.datetime] = None
    completed_at: Optional[dt.datetime] = None
    triggered_by_user_id: Optional[str] = None
    summary_json: dict[str, Any] | None = None
    error_text: Optional[str] = None
    source_version: Optional[str] = None
    fingerprint: Optional[str] = None
    created_at: Optional[dt.datetime] = None


def parse_signal_definitions(payload: list[dict[str, Any]] | None) -> list[SignalDefinition]:
    return TypeAdapter(list[SignalDefinition]).validate_python(payload or [])


def parse_data_sources(payload: list[dict[str, Any]] | None) -> list[DataSource]:
    return TypeAdapter(list[DataSource]).validate_python(payload or [])


def parse_observations(payload: list[dict[str, Any]] | None) -> list[SignalObservation]:
    return TypeAdapter(list[SignalObservation]).validate_python(payload or [])


def parse_intervals(payload: list[dict[str, Any]] | None) -> list[SignalInterval]:
    return TypeAdapter(list[SignalInterval]).validate_python(payload or [])


def parse_ingestion_runs(payload: list[dict[str, Any]] | None) -> list[IngestionRun]:
    return TypeAdapter(list[IngestionRun]).validate_python(payload or [])
