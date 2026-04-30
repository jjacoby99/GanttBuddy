from __future__ import annotations

import datetime as dt
from typing import Any, Literal, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class AnalyticsBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class Kpi(AnalyticsBaseModel):
    key: str
    label: str
    value: float | int | str | None
    unit: Optional[str] = None


class EventCountRow(AnalyticsBaseModel):
    event_type: str
    count: int


class SeriesPoint(AnalyticsBaseModel):
    x: dt.date
    y: float


class SeriesPointDT(AnalyticsBaseModel):
    x: dt.datetime
    y: float


class NamedSeries(AnalyticsBaseModel):
    name: str
    points: list[SeriesPoint] = Field(default_factory=list)


class NamedSeriesDT(AnalyticsBaseModel):
    name: str
    points: list[SeriesPointDT] = Field(default_factory=list)


class RelineMetadata(AnalyticsBaseModel):
    schema_version: int = 1
    site_id: str
    site_name: str
    mill_id: str
    mill_name: str
    vendor: str
    liner_system: str
    campaign_id: Optional[str] = None
    scope: Optional[str] = None
    liner_type: Optional[str] = None
    supervisor: str = ""
    notes: str = ""


class ProjectOverviewAnalytics(AnalyticsBaseModel):
    project_id: str
    as_of: dt.datetime
    kpis: list[Kpi] = Field(default_factory=list)
    events_by_type: list[EventCountRow] = Field(default_factory=list)
    task_counts: dict[str, int] = Field(default_factory=dict)


class BurnupAnalytics(AnalyticsBaseModel):
    project_id: str
    as_of: dt.datetime
    cumulative_planned_hours: list[SeriesPoint] = Field(default_factory=list)
    cumulative_actual_hours: list[SeriesPoint] = Field(default_factory=list)

    def to_frame(self) -> pd.DataFrame:
        planned = [
            {"x": point.x, "series": "Planned", "y": point.y}
            for point in self.cumulative_planned_hours
        ]
        actual = [
            {"x": point.x, "series": "Actual", "y": point.y}
            for point in self.cumulative_actual_hours
        ]
        df = pd.DataFrame(planned + actual)
        if df.empty:
            return pd.DataFrame(columns=["x", "series", "y"])
        df["x"] = pd.to_datetime(df["x"]).dt.date
        df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0.0)
        return df.sort_values(["x", "series"])


class PhaseBreakdownRow(AnalyticsBaseModel):
    phase_id: str
    phase_name: str
    task_count: int
    planned_hours: float
    actual_hours: float
    delta_hours: float
    pct_complete: float


class PhaseAnalytics(AnalyticsBaseModel):
    project_id: str
    as_of: dt.datetime
    rows: list[PhaseBreakdownRow] = Field(default_factory=list)


class TaskTypeBreakdownRow(AnalyticsBaseModel):
    task_type: str
    task_count: int
    planned_hours: float
    actual_hours: float


class TaskTypeAnalytics(AnalyticsBaseModel):
    project_id: str
    as_of: dt.datetime
    rows: list[TaskTypeBreakdownRow] = Field(default_factory=list)


class EventsTimelineAnalytics(AnalyticsBaseModel):
    project_id: str
    as_of: dt.datetime
    series: list[NamedSeries] = Field(default_factory=list)


class ProjectDashboardAnalytics(AnalyticsBaseModel):
    project_id: str
    as_of: dt.datetime
    metadata: dict[str, Any] | None = None
    reline_metadata: Optional[RelineMetadata] = None
    overview: ProjectOverviewAnalytics
    burnup: BurnupAnalytics
    by_phase: PhaseAnalytics
    by_task_type: TaskTypeAnalytics
    events_timeline: EventsTimelineAnalytics


class QuantityNormalizedSummary(AnalyticsBaseModel):
    task_count: int
    quantified_task_count: int
    planned_hours: float
    actual_hours: float
    quantified_actual_hours: float
    unquantified_actual_hours: float
    quantified_actual_hours_pct: float | None = None
    planned_rows: float
    actual_rows: float
    planned_liners: float
    actual_liners: float
    planned_hours_per_row: float | None = None
    actual_hours_per_row: float | None = None
    planned_hours_per_liner: float | None = None
    actual_hours_per_liner: float | None = None
    actual_rows_per_hour: float | None = None
    actual_liners_per_hour: float | None = None
    rows_attainment_ratio: float | None = None
    liners_attainment_ratio: float | None = None
    rows_variance_pct: float | None = None
    liners_variance_pct: float | None = None
    hours_per_row_variance_pct: float | None = None
    hours_per_liner_variance_pct: float | None = None


class QuantityNormalizedOverviewAnalytics(AnalyticsBaseModel):
    project_id: str
    as_of: dt.datetime
    kpis: list[Kpi] = Field(default_factory=list)
    summary: QuantityNormalizedSummary


class QuantityNormalizedBreakdownRow(QuantityNormalizedSummary):
    key: str
    label: str


class QuantityNormalizedBreakdownAnalytics(AnalyticsBaseModel):
    project_id: str
    as_of: dt.datetime
    grouping: Literal["work_type", "component", "work_type_component"]
    include_subcomponents: bool = False
    allocation_basis: str
    kpis: list[Kpi] = Field(default_factory=list)
    rows: list[QuantityNormalizedBreakdownRow] = Field(default_factory=list)

    def to_frame(self) -> pd.DataFrame:
        df = pd.DataFrame([row.model_dump() for row in self.rows])
        if df.empty:
            return pd.DataFrame()
        numeric_columns = [
            "task_count",
            "quantified_task_count",
            "planned_hours",
            "actual_hours",
            "quantified_actual_hours",
            "unquantified_actual_hours",
            "quantified_actual_hours_pct",
            "planned_rows",
            "actual_rows",
            "planned_liners",
            "actual_liners",
            "planned_hours_per_row",
            "actual_hours_per_row",
            "planned_hours_per_liner",
            "actual_hours_per_liner",
            "actual_rows_per_hour",
            "actual_liners_per_hour",
            "rows_attainment_ratio",
            "liners_attainment_ratio",
            "rows_variance_pct",
            "liners_variance_pct",
            "hours_per_row_variance_pct",
            "hours_per_liner_variance_pct",
        ]
        for column in numeric_columns:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce")
        return df.sort_values(["actual_hours", "planned_hours", "label"], ascending=[False, False, True])


class ShiftInchRow(AnalyticsBaseModel):
    crew_id: str
    crew_name: str
    shift_type: str
    shift_date: dt.date
    kpis: list[Kpi] = Field(default_factory=list)
    task_series: NamedSeriesDT


class InchingAnalytics(AnalyticsBaseModel):
    project_id: str
    as_of: dt.datetime
    kpis: list[Kpi] = Field(default_factory=list)
    series: list[NamedSeries] = Field(default_factory=list)
    shift_inch_performance: list[ShiftInchRow] = Field(default_factory=list)


def parse_dashboard_analytics(payload: dict | None) -> ProjectDashboardAnalytics:
    return ProjectDashboardAnalytics.model_validate(payload or {})


def parse_inching_analytics(payload: dict | None) -> InchingAnalytics:
    return InchingAnalytics.model_validate(payload or {})


def parse_normalized_overview(payload: dict | None) -> QuantityNormalizedOverviewAnalytics:
    return QuantityNormalizedOverviewAnalytics.model_validate(payload or {})


def parse_normalized_breakdown(payload: dict | None) -> QuantityNormalizedBreakdownAnalytics:
    return QuantityNormalizedBreakdownAnalytics.model_validate(payload or {})


def parse_normalized_breakdown_rows(payload: list[dict] | None) -> list[QuantityNormalizedBreakdownRow]:
    return TypeAdapter(list[QuantityNormalizedBreakdownRow]).validate_python(payload or [])
