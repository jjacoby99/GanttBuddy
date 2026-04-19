from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from logic.backend.api_client import fetch_analytics, fetch_inching_performance
from logic.backend.delays import get_delays
from logic.gantt_builder import build_timeline
from logic.post_mortem import PostMortemAnalyzer
from logic.powerpoint_report import FigureRequest, MillRelinePowerPointReport, TableRequest
from models.delay import DELAY_BADGE, Delay, DelayType
from models.gantt_state import GanttState
from models.phase import Phase
from models.project import Project
from models.project_metadata import RelineMetadata
from ui.utils.phase_delay_plot import generate_phase_delay_plot


class ReportExportError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReportArtifacts:
    excel: BytesIO
    powerpoint: BytesIO


def _metadata_replacements(project: Project, metadata: Optional[RelineMetadata]) -> dict[str, Any]:
    if metadata is None:
        return {
            "MILL_NAME": project.name,
        }

    return {
        "PROJECT_TITLE": project.name,
        "MILL_NAME": metadata.mill_name,
    }


def _plotly_png_provider(fig: go.Figure, *, width: int = 1600, height: int = 900, scale: int = 2):
    def _render() -> bytes:
        try:
            return pio.to_image(
                fig,
                format="png",
                width=width,
                height=height,
                scale=scale,
                engine="kaleido",
            )
        except Exception as exc:
            raise ReportExportError(
                "Static image export failed. Install the PowerPoint export dependencies "
                "(python-pptx and kaleido) to generate the report deck."
            ) from exc

    return _render


def _safe_get(d: dict[str, Any], *path: str, default=None):
    cur: Any = d
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _build_delay_summary(delays: list[Delay]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for delay in delays:
        delay_type = delay.delay_type
        label = DELAY_BADGE.get(delay_type, ("gray", "", str(delay_type)))[2]
        hours = max(float(delay.duration_minutes or 0), 0.0) / 60.0
        rows.append(
            {
                "delay_type": delay_type.value if isinstance(delay_type, DelayType) else str(delay_type),
                "delay_type_label": label,
                "hours": hours,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "DELAY TYPE",
                "COUNT",
                "FREQUENCY OF OCCURRENCE",
                "TOTAL DELAY (HRS)",
                "PERCENTAGE OF TOTAL DELAY",
            ]
        )

    df = pd.DataFrame(rows)
    summary = (
        df.groupby(["delay_type", "delay_type_label"], as_index=False)
        .agg(
            COUNT=("delay_type_label", "size"),
            TOTAL_DELAY_HOURS=("hours", "sum"),
        )
        .sort_values("TOTAL_DELAY_HOURS", ascending=False)
    )
    total_count = max(int(summary["COUNT"].sum()), 1)
    total_hours = max(float(summary["TOTAL_DELAY_HOURS"].sum()), 1e-9)
    summary["FREQUENCY OF OCCURRENCE"] = summary["COUNT"] / total_count
    summary["PERCENTAGE OF TOTAL DELAY"] = summary["TOTAL_DELAY_HOURS"] / total_hours

    return summary.rename(
        columns={
            "delay_type_label": "DELAY TYPE",
            "TOTAL_DELAY_HOURS": "TOTAL DELAY (HRS)",
        }
    )[
        [
            "DELAY TYPE",
            "COUNT",
            "FREQUENCY OF OCCURRENCE",
            "TOTAL DELAY (HRS)",
            "PERCENTAGE OF TOTAL DELAY",
        ]
    ]


def _format_delay_summary_for_table(summary: pd.DataFrame) -> pd.DataFrame:
    table_df = summary.copy()
    if table_df.empty:
        return table_df

    table_df["COUNT"] = table_df["COUNT"].map(lambda v: f"{int(v)}")
    table_df["FREQUENCY OF OCCURRENCE"] = table_df["FREQUENCY OF OCCURRENCE"].map(lambda v: f"{float(v):.1%}")
    table_df["TOTAL DELAY (HRS)"] = table_df["TOTAL DELAY (HRS)"].map(lambda v: f"{float(v):.1f}")
    table_df["PERCENTAGE OF TOTAL DELAY"] = table_df["PERCENTAGE OF TOTAL DELAY"].map(lambda v: f"{float(v):.1%}")
    return table_df


def _build_delay_count_figure(summary: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        summary.sort_values("COUNT", ascending=True),
        x="COUNT",
        y="DELAY TYPE",
        orientation="h",
        text="COUNT",
        color="DELAY TYPE",
        title="Count by delay type",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        template="plotly_white",
        showlegend=False,
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis_title="Count",
        yaxis_title="",
    )
    return fig


def _build_delay_hours_figure(summary: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        summary.sort_values("TOTAL DELAY (HRS)", ascending=True),
        x="TOTAL DELAY (HRS)",
        y="DELAY TYPE",
        orientation="h",
        text="TOTAL DELAY (HRS)",
        color="DELAY TYPE",
        title="Total hours by delay type",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        template="plotly_white",
        showlegend=False,
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis_title="Hours",
        yaxis_title="",
    )
    return fig


def _build_burnup_figure(dashboard: dict[str, Any]) -> go.Figure:
    planned = _safe_get(dashboard, "burnup", "cumulative_planned_hours", default=[]) or []
    actual = _safe_get(dashboard, "burnup", "cumulative_actual_hours", default=[]) or []

    fig = go.Figure()
    if planned:
        pdf = pd.DataFrame(planned)
        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(pdf["x"]),
                y=pd.to_numeric(pdf["y"], errors="coerce").fillna(0.0),
                mode="lines+markers",
                name="Planned",
            )
        )
    if actual:
        adf = pd.DataFrame(actual)
        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(adf["x"]),
                y=pd.to_numeric(adf["y"], errors="coerce").fillna(0.0),
                mode="lines+markers",
                name="Actual",
            )
        )

    fig.update_layout(
        template="plotly_white",
        title="Progress vs Plan",
        xaxis_title="Date",
        yaxis_title="Cumulative Hours",
        legend_title_text="",
        margin=dict(l=60, r=20, t=70, b=50),
    )
    return fig


def _build_inching_series_figure(
    payload: dict[str, Any],
    *,
    title: str,
    y_axis_title: str,
    allowed_series: set[str],
) -> go.Figure:
    fig = go.Figure()
    for series in payload.get("series") or []:
        name = series.get("name", "Series")
        if name not in allowed_series:
            continue
        points = pd.DataFrame(series.get("points") or [])
        if points.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(points["x"]),
                y=pd.to_numeric(points["y"], errors="coerce").fillna(0.0),
                mode="lines+markers",
                name=name,
            )
        )

    fig.update_layout(
        template="plotly_white",
        title=title,
        xaxis_title="Date",
        yaxis_title=y_axis_title,
        legend_title_text="",
        margin=dict(l=60, r=20, t=70, b=50),
    )
    return fig


def _build_phase_timeline_provider(phase: Phase, project_name: str):
    def _render() -> bytes:
        phase_project = Project(name=project_name)
        phase_project.add_phase(phase)

        fig = build_timeline(
            project=phase_project,
            inputs=GanttState(
                show_actual=True,
                show_planned=True,
                shade_non_working_time=False,
            ),
        )
        return _plotly_png_provider(fig, width=1800, height=950, scale=2)()

    return _render


def build_excel_report_buffer(project: Project, *, n: int = -1) -> BytesIO:
    workbook = PostMortemAnalyzer.write_post_mortem(project=project, n=n)
    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def build_powerpoint_report_buffer(
    *,
    project: Project,
    headers: dict[str, Any],
    metadata: Optional[RelineMetadata] = None,
    include_figures: bool = True,
) -> BytesIO:
    dashboard = fetch_analytics(headers=headers, project_id=project.uuid, date_from=None, date_to=None)
    inching = fetch_inching_performance(headers=headers, project_id=project.uuid, date_from=None, date_to=None)
    delays = get_delays(headers=headers, project_id=project.uuid, timezone=project.timezone)

    delay_summary = _build_delay_summary(delays)

    delay_count_fig = _build_delay_count_figure(delay_summary)
    delay_hours_fig = _build_delay_hours_figure(delay_summary)
    burnup_fig = _build_burnup_figure(dashboard)
    phase_delay_fig = generate_phase_delay_plot(project=project, units="hours")
    inching_fig = _build_inching_series_figure(
        inching,
        title="Avg inch time by date",
        y_axis_title="Avg inch time (min)",
        allowed_series={"Day shift avg inch time (min)", "Night shift avg inch time (min)"},
    )
    ttfi_fig = _build_inching_series_figure(
        inching,
        title="Time to First Inch - Day vs Night",
        y_axis_title="Time to first inch (min)",
        allowed_series={"Day Shift Time to First Inch (min)", "Night Shift Time to First Inch (min)"},
    )

    delay_raw_table = _format_delay_summary_for_table(delay_summary)
    slide_figures = {}
    timeline_figure_builders = None

    if include_figures:
        slide_figures = {
            "delay_types": [
                FigureRequest(
                    name="delay-counts",
                    producer=_plotly_png_provider(delay_count_fig, width=1000, height=800),
                    placement=MillRelinePowerPointReport.DEFAULT_FIGURE_PLACEMENTS["delay_types_left"],
                ),
                FigureRequest(
                    name="delay-hours",
                    producer=_plotly_png_provider(delay_hours_fig, width=1000, height=800),
                    placement=MillRelinePowerPointReport.DEFAULT_FIGURE_PLACEMENTS["delay_types_right"],
                ),
            ],
            "progress": [
                FigureRequest(
                    name="burnup",
                    producer=_plotly_png_provider(burnup_fig),
                    placement=MillRelinePowerPointReport.DEFAULT_FIGURE_PLACEMENTS["progress"],
                ),
            ],
            "phase_delay_chart": [
                FigureRequest(
                    name="phase-delay-chart",
                    producer=_plotly_png_provider(phase_delay_fig),
                    placement=MillRelinePowerPointReport.DEFAULT_FIGURE_PLACEMENTS["phase_delay_chart"],
                ),
            ],
            "inching_performance": [
                FigureRequest(
                    name="inching-performance",
                    producer=_plotly_png_provider(inching_fig),
                    placement=MillRelinePowerPointReport.DEFAULT_FIGURE_PLACEMENTS["inching_performance"],
                ),
            ],
            "ttfi": [
                FigureRequest(
                    name="ttfi",
                    producer=_plotly_png_provider(ttfi_fig),
                    placement=MillRelinePowerPointReport.DEFAULT_FIGURE_PLACEMENTS["ttfi"],
                ),
            ],
        }
        timeline_figure_builders = {
            pid: _build_phase_timeline_provider(project.phases[pid], project.name)
            for pid in project.phase_order
        }

    context = MillRelinePowerPointReport.build_context(
        project=project,
        replacements=_metadata_replacements(project, metadata),
        slide_figures=slide_figures,
        slide_tables={
            "delay_types_raw": TableRequest(
                dataframe=delay_raw_table,
                fallback_font_size_pt=11.0,
                fallback_bold=False,
            ),
        },
        timeline_figure_builders=timeline_figure_builders,
    )

    report = MillRelinePowerPointReport()
    buffer = BytesIO()
    presentation = report.render(context)
    presentation.save(buffer)
    buffer.seek(0)
    return buffer


def build_report_artifacts(
    *,
    project: Project,
    headers: dict[str, Any],
    metadata: Optional[RelineMetadata] = None,
) -> ReportArtifacts:
    excel = build_excel_report_buffer(project)
    powerpoint = build_powerpoint_report_buffer(
        project=project,
        headers=headers,
        metadata=metadata,
    )
    return ReportArtifacts(excel=excel, powerpoint=powerpoint)
