from __future__ import annotations

import datetime as dt
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class ForecastBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ForecastPoint(ForecastBaseModel):
    x: dt.datetime
    y: float


class ForecastTaskRow(ForecastBaseModel):
    task_id: str
    phase_id: str
    phase_name: str
    phase_position: int
    task_name: str
    task_position: int
    planned: bool
    status: str
    planned_start: Optional[dt.datetime] = None
    planned_end: Optional[dt.datetime] = None
    planned_duration_hours: float = 0.0
    actual_start: Optional[dt.datetime] = None
    actual_end: Optional[dt.datetime] = None
    actual_duration_hours: Optional[float] = None
    effective_start: Optional[dt.datetime] = None
    effective_end: Optional[dt.datetime] = None
    effective_duration_hours: float = 0.0
    is_completed: bool = False
    is_in_progress: bool = False


class ForecastResponse(ForecastBaseModel):
    project_id: str
    as_of: dt.datetime
    timezone_name: str
    has_actuals: bool
    planned_end: Optional[dt.datetime] = None
    forecast_end: Optional[dt.datetime] = None
    forecast_start: Optional[dt.datetime] = None
    total_planned_hours: float = 0.0
    earned_actual_hours: float = 0.0
    earned_planned_hours: float = 0.0
    unplanned_hours: float = 0.0
    planned_cumulative_hours: list[ForecastPoint] = Field(default_factory=list)
    actual_forecast_cumulative_hours: list[ForecastPoint] = Field(default_factory=list)
    tasks: list[ForecastTaskRow] = Field(default_factory=list)

    @property
    def timezone(self) -> ZoneInfo:
        try:
            return ZoneInfo(self.timezone_name)
        except Exception:
            return ZoneInfo("UTC")

    def _to_local(self, value: Optional[dt.datetime]) -> Optional[dt.datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.UTC)
        return value.astimezone(self.timezone)

    def series_to_frame(self) -> pd.DataFrame:
        planned_df = pd.DataFrame(
            [{"time": self._to_local(point.x), "planned_cum_hours": point.y} for point in self.planned_cumulative_hours]
        )
        actual_df = pd.DataFrame(
            [
                {"time": self._to_local(point.x), "actual_forecast_cum_hours": point.y}
                for point in self.actual_forecast_cumulative_hours
            ]
        )

        if planned_df.empty and actual_df.empty:
            return pd.DataFrame(columns=["time", "planned_cum_hours", "actual_forecast_cum_hours"])

        if planned_df.empty:
            merged = actual_df.copy()
        elif actual_df.empty:
            merged = planned_df.copy()
        else:
            merged = planned_df.merge(actual_df, on="time", how="outer")

        merged = merged.sort_values("time").reset_index(drop=True)
        if "planned_cum_hours" not in merged:
            merged["planned_cum_hours"] = 0.0
        if "actual_forecast_cum_hours" not in merged:
            merged["actual_forecast_cum_hours"] = 0.0
        merged["planned_cum_hours"] = pd.to_numeric(merged["planned_cum_hours"], errors="coerce").fillna(0.0)
        merged["actual_forecast_cum_hours"] = (
            pd.to_numeric(merged["actual_forecast_cum_hours"], errors="coerce").fillna(0.0)
        )
        return merged

    def tasks_to_frame(self) -> pd.DataFrame:
        rows: list[dict[str, object]] = []
        for task in sorted(self.tasks, key=lambda item: (item.phase_position, item.task_position)):
            rows.append(
                {
                    "name": task.task_name,
                    "phase": task.phase_name,
                    "planned_start": self._to_local(task.planned_start),
                    "planned_finish": self._to_local(task.planned_end),
                    "planned_duration": task.planned_duration_hours,
                    "actual_start": self._to_local(task.actual_start),
                    "actual_finish": self._to_local(task.actual_end),
                    "actual_duration": task.actual_duration_hours,
                }
            )
        return pd.DataFrame(rows)


def parse_forecast_response(payload: dict | None) -> ForecastResponse:
    return ForecastResponse.model_validate(payload or {})


def parse_forecast_task_rows(payload: list[dict] | None) -> list[ForecastTaskRow]:
    return TypeAdapter(list[ForecastTaskRow]).validate_python(payload or [])
