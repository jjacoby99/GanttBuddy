from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Literal, Optional

import altair as alt
import pandas as pd
import streamlit as st

from logic.backend.api_client import (
    fetch_analytics,
    fetch_inching_performance,
    fetch_normalized_by_work_type_and_component,
    fetch_normalized_overview,
)
from logic.backend.utils.parse_datetime import parse_backend_utc
from models.analytics import (
    InchingAnalytics,
    ProjectDashboardAnalytics,
    QuantityNormalizedBreakdownAnalytics,
    QuantityNormalizedOverviewAnalytics,
)
from models.task import TaskType
from ui.create_project import create_project
from ui.utils.page_header import render_registered_page_header
from ui.utils.phase_delay_plot import generate_phase_delay_plot


st.set_page_config(page_title="Analytics", layout="wide")


def _fmt_num(value: Any, *, decimals: int = 2) -> str:
    if value is None:
        return "-"
    try:
        if isinstance(value, int) and decimals == 0:
            return f"{value:,}"
        numeric = float(value)
        if math.isfinite(numeric):
            return f"{numeric:,.{decimals}f}"
    except Exception:
        pass
    return str(value)


def _fmt_pct(value: Any, *, decimals: int = 1, already_percent: bool = False) -> str:
    if value is None:
        return "-"
    try:
        numeric = float(value)
        pct = numeric if already_percent else numeric * 100.0
        return f"{pct:.{decimals}f}%"
    except Exception:
        return str(value)


def _fmt_signed_pct(value: Any, *, decimals: int = 1) -> str:
    if value is None:
        return "-"
    try:
        numeric = float(value) * 100.0
        return f"{numeric:+.{decimals}f}%"
    except Exception:
        return str(value)


def _normalize_task_type(value: str) -> str:
    if not value:
        return "UNKNOWN"
    return value.split(".")[-1]


def _card_css() -> None:
    st.markdown(
        """
        <style>
        .gb-card {
            border: 1px solid rgba(33, 43, 54, 0.10);
            border-radius: 18px;
            padding: 18px 18px 14px 18px;
            background:
                linear-gradient(180deg, rgba(255,255,255,0.98), rgba(246,248,250,0.96));
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
        }
        .gb-hero {
            border: 1px solid rgba(33, 43, 54, 0.08);
            border-radius: 24px;
            padding: 24px;
            background:
                radial-gradient(circle at top left, rgba(26, 115, 232, 0.10), transparent 34%),
                radial-gradient(circle at bottom right, rgba(16, 185, 129, 0.10), transparent 28%),
                linear-gradient(180deg, rgba(255,255,255,0.98), rgba(243,246,249,0.96));
            box-shadow: 0 14px 34px rgba(15, 23, 42, 0.07);
        }
        .gb-title {
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: rgba(49, 51, 63, 0.62);
            margin-bottom: 8px;
            font-weight: 700;
        }
        .gb-value {
            font-size: 30px;
            line-height: 1.05;
            font-weight: 800;
            color: rgba(17, 24, 39, 0.96);
        }
        .gb-sub {
            margin-top: 8px;
            font-size: 12px;
            color: rgba(49, 51, 63, 0.68);
        }
        .gb-banner {
            border-radius: 16px;
            padding: 12px 14px;
            font-size: 14px;
            margin-bottom: 12px;
            border: 1px solid transparent;
        }
        .gb-banner-warn {
            background: rgba(245, 158, 11, 0.10);
            border-color: rgba(245, 158, 11, 0.22);
            color: rgba(146, 64, 14, 1);
        }
        .gb-banner-good {
            background: rgba(16, 185, 129, 0.10);
            border-color: rgba(16, 185, 129, 0.22);
            color: rgba(6, 95, 70, 1);
        }
        .gb-pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            margin-top: 10px;
        }
        .pill-good {
            background: rgba(16, 185, 129, 0.10);
            color: rgba(6, 95, 70, 1);
        }
        .pill-bad {
            background: rgba(239, 68, 68, 0.10);
            color: rgba(153, 27, 27, 1);
        }
        .pill-neutral {
            background: rgba(59, 130, 246, 0.10);
            color: rgba(30, 64, 175, 1);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _kpi_card(title: str, value: str, subtitle: str = "", pill: tuple[str, str] | None = None) -> None:
    pill_html = ""
    if pill:
        pill_html = f'<div class="gb-pill {pill[1]}">{pill[0]}</div>'
    st.markdown(
        f"""
        <div class="gb-card">
          <div class="gb-title">{title}</div>
          <div class="gb-value">{value}</div>
          <div class="gb-sub">{subtitle}</div>
          {pill_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _banner(message: str, *, state: Literal["warn", "good"]) -> None:
    st.markdown(
        f'<div class="gb-banner gb-banner-{"warn" if state == "warn" else "good"}">{message}</div>',
        unsafe_allow_html=True,
    )


def _kpi_value(kpis: list[Any], key: str) -> tuple[Any, Any]:
    for item in kpis:
        if item.key == key:
            return item.value, item.unit
    return None, None


_COMPONENT_KPI_SPECS: list[tuple[str, str]] = [
    ("strip_feed", "Strip Feed"),
    ("strip_shell", "Strip Shell"),
    ("strip_discharge", "Strip Discharge"),
    ("install_feed", "Install Feed"),
    ("install_shell", "Install Shell"),
    ("install_discharge", "Install Discharge"),
]


def _component_kpi_keys() -> set[str]:
    keys: set[str] = set()
    for prefix, _label in _COMPONENT_KPI_SPECS:
        keys.add(f"{prefix}_rows")
        keys.add(f"{prefix}_pieces")
    return keys


def _dashboard_phase_frame(dashboard: ProjectDashboardAnalytics) -> pd.DataFrame:
    df = pd.DataFrame([row.model_dump() for row in dashboard.by_phase.rows])
    if df.empty:
        return pd.DataFrame(columns=["phase_name", "task_count", "planned_hours", "actual_hours", "delta_hours", "pct_complete"])
    df["phase_name"] = df["phase_name"].astype(str)
    for column in ["task_count", "planned_hours", "actual_hours", "delta_hours", "pct_complete"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)
    grouped = df.groupby("phase_name", as_index=False).agg(
        task_count=("task_count", "sum"),
        planned_hours=("planned_hours", "sum"),
        actual_hours=("actual_hours", "sum"),
    )
    grouped["delta_hours"] = grouped["actual_hours"] - grouped["planned_hours"]
    weighted_complete = (
        df.groupby("phase_name")
        .apply(lambda frame: (frame["pct_complete"] * frame["planned_hours"]).sum() / max(frame["planned_hours"].sum(), 1e-9))
        .rename("pct_complete")
    )
    grouped = grouped.merge(weighted_complete, left_on="phase_name", right_index=True, how="left")
    grouped["pct_complete"] = grouped["pct_complete"].fillna(df.groupby("phase_name")["pct_complete"].mean())
    return grouped.sort_values("planned_hours", ascending=False)


def _dashboard_task_type_frame(dashboard: ProjectDashboardAnalytics) -> pd.DataFrame:
    df = pd.DataFrame([row.model_dump() for row in dashboard.by_task_type.rows])
    if df.empty:
        return pd.DataFrame(columns=["task_type", "task_count", "planned_hours", "actual_hours", "delta_hours"])
    df["task_type"] = df["task_type"].astype(str).map(_normalize_task_type)
    for column in ["task_count", "planned_hours", "actual_hours"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)
    df["delta_hours"] = df["actual_hours"] - df["planned_hours"]
    return df.sort_values("planned_hours", ascending=False)


def _events_frames(dashboard: ProjectDashboardAnalytics) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_type = pd.DataFrame([row.model_dump() for row in dashboard.overview.events_by_type])
    if not by_type.empty:
        by_type["count"] = pd.to_numeric(by_type["count"], errors="coerce").fillna(0).astype(int)

    rows: list[dict[str, Any]] = []
    for series in dashboard.events_timeline.series:
        for point in series.points:
            rows.append({"event_type": series.name, "x": point.x, "y": point.y})
    timeline = pd.DataFrame(rows)
    if not timeline.empty:
        timeline["x"] = pd.to_datetime(timeline["x"]).dt.date
        timeline["y"] = pd.to_numeric(timeline["y"], errors="coerce").fillna(0.0)
    return by_type, timeline


def _inching_shift_frame(payload: InchingAnalytics) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in payload.shift_inch_performance:
        row = {
            "crew": item.crew_name,
            "shift_type": str(item.shift_type).split(".")[-1],
            "shift_date": item.shift_date,
        }
        for key in ("avg_inch_time", "min_inch_time", "max_inch_time", "inch_count"):
            row[key] = next((kpi.value for kpi in item.kpis if kpi.key == key), None)
        rows.append(row)

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["shift_date", "shift_type", "crew", "avg_inch_time", "min_inch_time", "max_inch_time", "inch_count"])
    df["shift_date"] = pd.to_datetime(df["shift_date"]).dt.date
    for column in ["avg_inch_time", "min_inch_time", "max_inch_time"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["inch_count"] = pd.to_numeric(df["inch_count"], errors="coerce").fillna(0).astype(int)
    return df.sort_values(["shift_date", "shift_type", "crew"])


def _inching_series_frame(payload: InchingAnalytics, start_dt: Optional[datetime] = None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for series in payload.series:
        for point in series.points:
            rows.append({"series": series.name, "x": point.x, "y": point.y})
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["x", "series", "y"])
    df["x"] = pd.to_datetime(df["x"]).dt.date
    if isinstance(start_dt, datetime):
        df = df[df["x"] >= start_dt.date()]
    return df.sort_values(["x", "series"])


def _coverage_pill(coverage: float | None) -> tuple[str, str] | None:
    if coverage is None:
        return None
    if coverage < 0.8:
        return (f"{_fmt_pct(coverage)} coverage", "pill-bad")
    if coverage < 0.95:
        return (f"{_fmt_pct(coverage)} coverage", "pill-neutral")
    return (f"{_fmt_pct(coverage)} coverage", "pill-good")


def _variance_pill(value: float | None, *, inverse_good: bool = False) -> tuple[str, str] | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except Exception:
        return None
    is_good = numeric < 0 if inverse_good else numeric > 0
    if abs(numeric) < 0.001:
        tone = "pill-neutral"
    else:
        tone = "pill-good" if is_good else "pill-bad"
    return (_fmt_signed_pct(numeric), tone)


def _chart_burnup(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No burnup data yet.")
        return
    chart = (
        alt.Chart(df)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("x:T", title=None),
            y=alt.Y("y:Q", title="Cumulative hours"),
            color=alt.Color("series:N", title=None, scale=alt.Scale(range=["#1d4ed8", "#ef4444"])),
            tooltip=[
                alt.Tooltip("x:T", title="Date"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("y:Q", title="Hours", format=",.2f"),
            ],
        )
        .properties(height=330)
    )
    st.altair_chart(chart, width="stretch")


def _chart_task_type_hours(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No task type data yet.")
        return
    melted = df.melt(
        id_vars=["task_type"],
        value_vars=["planned_hours", "actual_hours"],
        var_name="series",
        value_name="hours",
    )
    melted["series"] = melted["series"].map({"planned_hours": "Planned", "actual_hours": "Actual"})
    chart = (
        alt.Chart(melted)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("task_type:N", title=None, sort="-y"),
            y=alt.Y("hours:Q", title="Hours"),
            xOffset="series:N",
            color=alt.Color("series:N", title=None, scale=alt.Scale(range=["#93c5fd", "#2563eb"])),
            tooltip=[
                alt.Tooltip("task_type:N", title="Task type"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("hours:Q", title="Hours", format=",.2f"),
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(chart, width="stretch")


def _chart_events_timeline(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No event timeline data yet.")
        return
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("x:T", title=None),
            y=alt.Y("y:Q", title="Events"),
            color=alt.Color("event_type:N", title=None),
            tooltip=[
                alt.Tooltip("x:T", title="Date"),
                alt.Tooltip("event_type:N", title="Event type"),
                alt.Tooltip("y:Q", title="Count"),
            ],
        )
        .properties(height=260)
    )
    st.altair_chart(chart, width="stretch")


def _chart_combined_hours_per_row(payload: QuantityNormalizedBreakdownAnalytics) -> None:
    df = payload.to_frame()
    if df.empty:
        st.info("No normalized breakdown data yet.")
        return
    frame = df[
        [
            "label",
            "actual_hours_per_row",
            "planned_hours_per_row",
            "hours_per_row_variance_pct",
            "quantified_actual_hours_pct",
        ]
    ].copy()
    frame = frame.dropna(subset=["actual_hours_per_row"]).head(12)
    if frame.empty:
        st.info("Hours-per-row comparisons are not available yet because the denominator is zero.")
        return
    chart = (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=8)
        .encode(
            y=alt.Y("label:N", title=None, sort="-x"),
            x=alt.X("actual_hours_per_row:Q", title="Actual hours / row"),
            color=alt.Color(
                "hours_per_row_variance_pct:Q",
                title="Vs plan",
                scale=alt.Scale(
                    domain=[-0.25, 0, 0.25],
                    range=["#10b981", "#93c5fd", "#ef4444"],
                ),
            ),
            tooltip=[
                alt.Tooltip("label:N", title="Bucket"),
                alt.Tooltip("actual_hours_per_row:Q", title="Actual hours / row", format=",.3f"),
                alt.Tooltip("planned_hours_per_row:Q", title="Planned hours / row", format=",.3f"),
                alt.Tooltip("hours_per_row_variance_pct:Q", title="Variance", format="+.1%"),
                alt.Tooltip("quantified_actual_hours_pct:Q", title="Coverage", format=".0%"),
            ],
        )
        .properties(height=max(280, min(34 * len(frame), 440)))
    )
    st.altair_chart(chart, width="stretch")


def _chart_inching_series(df: pd.DataFrame, *, title: str, units: str) -> None:
    if df.empty:
        st.info("No inching timeseries data yet.")
        return
    chart = (
        alt.Chart(df)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("x:T", title="Date"),
            y=alt.Y("y:Q", title=f"{title} ({units})"),
            color=alt.Color("series:N", title=None),
            tooltip=[
                alt.Tooltip("x:T", title="Date"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("y:Q", title=title, format=",.2f"),
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(chart, width="stretch")


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_dashboard(project_id: str, date_from: Optional[date], date_to: Optional[date]) -> ProjectDashboardAnalytics:
    headers = st.session_state.get("auth_headers", {})
    pid = st.session_state.get("project_id") or st.session_state.session.project.uuid
    return fetch_analytics(headers=headers, project_id=pid, date_from=date_from, date_to=date_to)


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_inching(project_id: str, date_from: Optional[date], date_to: Optional[date]) -> InchingAnalytics:
    headers = st.session_state.get("auth_headers", {})
    pid = st.session_state.get("project_id") or st.session_state.session.project.uuid
    return fetch_inching_performance(headers=headers, project_id=pid, date_from=date_from, date_to=date_to)


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_normalized_bundle(
    project_id: str,
) -> tuple[
    QuantityNormalizedOverviewAnalytics,
    QuantityNormalizedBreakdownAnalytics,
]:
    headers = st.session_state.get("auth_headers", {})
    pid = st.session_state.get("project_id") or st.session_state.session.project.uuid
    overview = fetch_normalized_overview(headers=headers, project_id=pid)
    work_type_component = fetch_normalized_by_work_type_and_component(headers=headers, project_id=pid)
    return overview, work_type_component


def _render_project_header(dashboard: ProjectDashboardAnalytics) -> None:
    metadata = dashboard.reline_metadata
    raw_meta = dashboard.metadata or {}
    site_name = metadata.site_name if metadata else raw_meta.get("site_name", "-")
    mill_name = metadata.mill_name if metadata else raw_meta.get("mill_name", "-")
    vendor = metadata.vendor if metadata else raw_meta.get("vendor", "-")
    liner_system = metadata.liner_system if metadata else raw_meta.get("liner_system", "-")
    scope = metadata.scope if metadata else raw_meta.get("scope", "-")
    campaign = metadata.campaign_id if metadata else raw_meta.get("campaign_id", "-")
    supervisor = metadata.supervisor if metadata else raw_meta.get("supervisor", "-")
    notes = (metadata.notes if metadata else raw_meta.get("notes", "")) or ""

    project_tz = st.session_state.session.project.timezone
    as_of = parse_backend_utc(dashboard.as_of.isoformat(), project_tz)

    left, right = st.columns([2.2, 1])
    with left:
        st.markdown(
            f"""
            <div class="gb-hero">
              <div class="gb-title">Project context</div>
              <div class="gb-value" style="font-size:24px;">{site_name} · {mill_name}</div>
              <div class="gb-sub">
                Vendor: <b>{vendor}</b> · Liner system: <b>{liner_system}</b> ·
                Scope: <b>{scope or "-"}</b> · Campaign: <b>{campaign or "-"}</b>
              </div>
              <div class="gb-sub">Supervisor: <b>{supervisor or "-"}</b> · As of: {as_of.strftime("%Y-%m-%d %H:%M")}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"""
            <div class="gb-card">
              <div class="gb-title">Notes</div>
              <div class="gb-sub" style="font-size:14px; line-height:1.45; color: rgba(49, 51, 63, 0.84);">
                {notes.strip() or "No notes provided."}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_overview_kpis(dashboard: ProjectDashboardAnalytics) -> None:
    kpis = {item.key: item for item in dashboard.overview.kpis}
    task_counts = dashboard.overview.task_counts or {}

    task_count = kpis.get("task_count").value if kpis.get("task_count") else None
    planned_hours = kpis.get("planned_hours").value if kpis.get("planned_hours") else None
    actual_hours = kpis.get("actual_hours").value if kpis.get("actual_hours") else None
    delta_hours = kpis.get("delta_hours").value if kpis.get("delta_hours") else None
    pct_complete = kpis.get("pct_complete").value if kpis.get("pct_complete") else None

    delta_pill: tuple[str, str] | None = None
    try:
        delta_numeric = float(delta_hours)
        if delta_numeric < -0.01:
            delta_pill = ("Under plan", "pill-good")
        elif delta_numeric > 0.01:
            delta_pill = ("Over plan", "pill-bad")
        else:
            delta_pill = ("On plan", "pill-neutral")
    except Exception:
        pass

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        _kpi_card(
            "Tasks",
            _fmt_num(task_count, decimals=0),
            f"Done: {task_counts.get('done', '-')} · Remaining: {task_counts.get('not_done', '-')}",
        )
    with c2:
        _kpi_card("Planned Hours", f"{_fmt_num(planned_hours)} h", f"Planned tasks: {task_counts.get('planned', '-')}")
    with c3:
        _kpi_card("Actual Hours", f"{_fmt_num(actual_hours)} h", f"Unplanned tasks: {task_counts.get('unplanned', '-')}")
    with c4:
        _kpi_card("Delta (A - P)", f"{_fmt_num(delta_hours)} h", "Negative is good", pill=delta_pill)
    with c5:
        _kpi_card("Complete", _fmt_pct(pct_complete, already_percent=True), "Based on task completion")


def _render_progress_tab(dashboard: ProjectDashboardAnalytics) -> None:
    left, right = st.columns([4.6, 1.4])
    with left:
        st.subheader("Progress vs Plan")
        burnup_df = dashboard.burnup.to_frame()
        _chart_burnup(burnup_df)
        if not burnup_df.empty:
            latest = burnup_df.sort_values("x").groupby("series").tail(1).set_index("series")
            planned_end = float(latest.loc["Planned", "y"]) if "Planned" in latest.index else None
            actual_end = float(latest.loc["Actual", "y"]) if "Actual" in latest.index else None
            if planned_end is not None and actual_end is not None:
                st.caption(f"End-of-window actual minus planned: {_fmt_num(actual_end - planned_end)} h")
    with right:
        kpis = {item.key: item for item in dashboard.overview.kpis}
        _kpi_card("Planned Rows", _fmt_num(kpis.get("planned_rows").value if kpis.get("planned_rows") else None, decimals=1), "Total planned scope")
        _kpi_card("Actual Rows", _fmt_num(kpis.get("actual_rows").value if kpis.get("actual_rows") else None, decimals=1), "Completed scope")
        _kpi_card("Planned Liners", _fmt_num(kpis.get("planned_liners").value if kpis.get("planned_liners") else None, decimals=0), "Expected liners")
        _kpi_card("Actual Liners", _fmt_num(kpis.get("actual_liners").value if kpis.get("actual_liners") else None, decimals=0), "Installed liners")


def _render_breakdowns_tab(dashboard: ProjectDashboardAnalytics) -> None:
    left, right = st.columns([2, 1])
    with left:
        st.subheader("By Phase")
        figure = generate_phase_delay_plot(project=st.session_state.session.project, units="hours")
        st.plotly_chart(figure, width="stretch")
    with right:
        phase_df = _dashboard_phase_frame(dashboard)
        if phase_df.empty:
            st.info("No phase data yet.")
        else:
            display = phase_df.rename(
                columns={
                    "phase_name": "Phase",
                    "task_count": "Tasks",
                    "planned_hours": "Planned (h)",
                    "actual_hours": "Actual (h)",
                    "delta_hours": "Delta (h)",
                    "pct_complete": "Complete (%)",
                }
            ).copy()
            display["Complete (%)"] = (display["Complete (%)"] * 100.0).round(1)
            st.dataframe(display, width="stretch", hide_index=True)

    st.divider()
    st.subheader("By Task Type")
    task_type_df = _dashboard_task_type_frame(dashboard)
    if not task_type_df.empty:
        generic_row = task_type_df[task_type_df["task_type"] == "GENERIC"]
        if not generic_row.empty:
            fraction = float(generic_row["task_count"].iloc[0]) / max(float(task_type_df["task_count"].sum()), 1.0)
            if fraction > 0.6:
                st.warning(f"Task type data is still dominated by GENERIC ({fraction:.0%} of tasks).")
    _chart_task_type_hours(task_type_df)
    if not task_type_df.empty:
        table = task_type_df.rename(
            columns={
                "task_type": "Task Type",
                "task_count": "Tasks",
                "planned_hours": "Planned (h)",
                "actual_hours": "Actual (h)",
                "delta_hours": "Delta (h)",
            }
        ).copy()
        for column in ["Planned (h)", "Actual (h)", "Delta (h)"]:
            table[column] = table[column].round(2)
        st.dataframe(table, width="stretch", hide_index=True)

    st.divider()
    st.subheader("Event Timeline")
    _, timeline_df = _events_frames(dashboard)
    _chart_events_timeline(timeline_df)


def _render_normalized_overview(overview: QuantityNormalizedOverviewAnalytics) -> None:
    summary = overview.summary
    coverage = summary.quantified_actual_hours_pct
    if coverage is not None and coverage < 0.8:
        _banner(
            f"Only {_fmt_pct(coverage)} of actual hours have quantity metadata. Compare rates carefully until coverage improves.",
            state="warn",
        )
    else:
        _banner(
            f"Quantity coverage is {_fmt_pct(coverage)} of actual hours, so these normalized rates are in a healthy range for project comparison.",
            state="good",
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        _kpi_card(
            "Coverage",
            _fmt_pct(summary.quantified_actual_hours_pct),
            f"{_fmt_num(summary.quantified_actual_hours)} h quantified",
            pill=_coverage_pill(summary.quantified_actual_hours_pct),
        )
    with c2:
        _kpi_card(
            "Hours / Row",
            _fmt_num(summary.actual_hours_per_row, decimals=3),
            f"Plan: {_fmt_num(summary.planned_hours_per_row, decimals=3)}",
            pill=_variance_pill(summary.hours_per_row_variance_pct, inverse_good=True),
        )
    with c3:
        _kpi_card(
            "Hours / Piece",
            _fmt_num(summary.actual_hours_per_liner, decimals=3),
            f"Plan: {_fmt_num(summary.planned_hours_per_liner, decimals=3)}",
            pill=_variance_pill(summary.hours_per_liner_variance_pct, inverse_good=True),
        )
    with c4:
        _kpi_card(
            "Rows Complete",
            _fmt_num(summary.actual_rows, decimals=1),
            f"Planned: {_fmt_num(summary.planned_rows, decimals=1)}",
            pill=_variance_pill(summary.rows_variance_pct),
        )
    with c5:
        _kpi_card(
            "Pieces Complete",
            _fmt_num(summary.actual_liners, decimals=0),
            f"Planned: {_fmt_num(summary.planned_liners, decimals=0)}",
            pill=_variance_pill(summary.liners_variance_pct),
        )

    detail_left, detail_right = st.columns([2.2, 1.8])
    with detail_left:
        st.caption(
            f"Quantified tasks: {_fmt_num(summary.quantified_task_count, decimals=0)} of {_fmt_num(summary.task_count, decimals=0)}. "
            f"Unquantified hours: {_fmt_num(summary.unquantified_actual_hours)} h."
        )
    with detail_right:
        st.caption(
            f"Rows / hour: {_fmt_num(summary.actual_rows_per_hour, decimals=3)}. "
            f"Pieces / hour: {_fmt_num(summary.actual_liners_per_hour, decimals=3)}."
        )


def _render_component_quantity_kpis(
    overview: QuantityNormalizedOverviewAnalytics,
    combined: QuantityNormalizedBreakdownAnalytics,
) -> None:
    kpi_map = {item.key: item for item in overview.kpis if item.key in _component_kpi_keys()}
    if not kpi_map:
        kpi_map = {item.key: item for item in combined.kpis if item.key in _component_kpi_keys()}
    if not kpi_map:
        return

    st.subheader("Strip / Install Component Counts")
    rows: list[dict[str, Any]] = []
    for prefix, label in _COMPONENT_KPI_SPECS:
        rows.append(
            {
                "Bucket": label,
                "Rows (Actual / Planned)": kpi_map.get(f"{prefix}_rows").value if kpi_map.get(f"{prefix}_rows") else None,
                "Pieces (Actual / Planned)": kpi_map.get(f"{prefix}_pieces").value if kpi_map.get(f"{prefix}_pieces") else None,
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True)


def _render_normalized_tab(project_id: str, refresh: bool) -> None:
    st.caption(
        "This view uses the project summary plus the combined strip/install-by-component breakdown so the comparison stays focused on the highest-signal reline data."
    )

    if refresh:
        _fetch_normalized_bundle.clear()
        fetch_normalized_overview.clear()
        fetch_normalized_by_work_type_and_component.clear()

    try:
        overview, work_type_component = _fetch_normalized_bundle(project_id)
    except Exception as exc:
        st.error(f"Failed to load normalized analytics: {exc}")
        return

    _render_normalized_overview(overview)
    _render_component_quantity_kpis(overview, work_type_component)

    st.divider()
    st.subheader("Strip / Install by Component")
    st.caption(work_type_component.allocation_basis)
    _chart_combined_hours_per_row(work_type_component)
    combined_df = work_type_component.to_frame()
    if not combined_df.empty:
        table = combined_df[
            [
                "label",
                "task_count",
                "quantified_actual_hours_pct",
                "planned_hours_per_row",
                "actual_hours_per_row",
                "hours_per_row_variance_pct",
                "planned_hours_per_liner",
                "actual_hours_per_liner",
                "hours_per_liner_variance_pct",
                "actual_rows",
                "planned_rows",
                "rows_variance_pct",
                "actual_liners",
                "planned_liners",
                "liners_variance_pct",
            ]
        ].rename(
            columns={
                "label": "Work Type / Component",
                "task_count": "Tasks",
                "quantified_actual_hours_pct": "Coverage",
                "planned_hours_per_row": "Plan Hours / Row",
                "actual_hours_per_row": "Hours / Row",
                "hours_per_row_variance_pct": "Row Variance",
                "planned_hours_per_liner": "Plan Hours / Piece",
                "actual_hours_per_liner": "Hours / Piece",
                "hours_per_liner_variance_pct": "Piece Variance",
                "actual_rows": "Actual Rows",
                "planned_rows": "Planned Rows",
                "rows_variance_pct": "Rows Variance",
                "actual_liners": "Actual Pieces",
                "planned_liners": "Planned Pieces",
                "liners_variance_pct": "Pieces Variance",
            }
        )
        for column in ["Coverage", "Row Variance", "Piece Variance", "Rows Variance", "Pieces Variance"]:
            table[column] = table[column].map(lambda value: _fmt_pct(value) if pd.notna(value) else "-")
        st.dataframe(table, width="stretch", hide_index=True)


def _render_inching_tab(project_id: str, date_from: Optional[date], date_to: Optional[date], refresh: bool) -> None:
    if refresh:
        _fetch_inching.clear()
        fetch_inching_performance.clear()
    try:
        inching = _fetch_inching(project_id, date_from, date_to)
    except Exception as exc:
        st.error(f"Failed to load inching performance: {exc}")
        return

    if not inching.kpis and not inching.shift_inch_performance:
        st.info("No inching data available yet.")
        return

    kpis = inching.kpis
    project_avg, _ = _kpi_value(kpis, "Project_avg")
    project_min, _ = _kpi_value(kpis, "Project_min")
    project_max, _ = _kpi_value(kpis, "Project_max")
    project_count, _ = _kpi_value(kpis, "Project_count")
    day_avg, _ = _kpi_value(kpis, "Day shift_avg")
    night_avg, _ = _kpi_value(kpis, "Night shift_avg")

    planned_avg = st.session_state.session.project.average_planned_duration(TaskType.INCH) * 60
    avg_pill: tuple[str, str] | None = None
    if project_avg is not None:
        try:
            if planned_avg > float(project_avg):
                avg_pill = (f"Plan: {_fmt_num(planned_avg)} min", "pill-good")
            elif planned_avg < float(project_avg):
                avg_pill = (f"Plan: {_fmt_num(planned_avg)} min", "pill-bad")
            else:
                avg_pill = ("On plan", "pill-neutral")
        except Exception:
            pass

    compare_pill: tuple[str, str] | None = None
    try:
        if day_avg is not None and night_avg is not None:
            day_numeric = float(day_avg)
            night_numeric = float(night_avg)
            if day_numeric < night_numeric - 0.01:
                compare_pill = (f"Day {_fmt_num(night_numeric - day_numeric)} min faster", "pill-neutral")
            elif night_numeric < day_numeric - 0.01:
                compare_pill = (f"Night {_fmt_num(day_numeric - night_numeric)} min faster", "pill-neutral")
            else:
                compare_pill = ("Similar", "pill-neutral")
    except Exception:
        pass

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _kpi_card("Project Avg", f"{_fmt_num(project_avg)} min", "All inch tasks", pill=avg_pill)
    with c2:
        _kpi_card("Fastest", f"{_fmt_num(project_min)} min", "Shortest inch observed")
    with c3:
        _kpi_card("Slowest", f"{_fmt_num(project_max)} min", "Longest inch observed")
    with c4:
        _kpi_card("Count", _fmt_num(project_count, decimals=0), "Completed inch tasks", pill=compare_pill)

    left, right = st.columns([3, 1.3])
    with left:
        st.subheader("Average Inch Time by Date")
        cutoff = st.session_state.session.project.first_ttfi_cutoff
        series_df = _inching_series_frame(inching, start_dt=cutoff)
        avg_series = series_df[series_df["series"].isin(["Day shift avg inch time (min)", "Night shift avg inch time (min)"])].copy()
        _chart_inching_series(avg_series, title="Avg inch time", units="min")
    with right:
        _kpi_card("Day Avg", f"{_fmt_num(day_avg)} min", "Average day shift inch time")
        _kpi_card("Night Avg", f"{_fmt_num(night_avg)} min", "Average night shift inch time")

    st.divider()
    st.subheader("Time to First Inch")
    ttfi_df = series_df[series_df["series"].isin(["Day Shift Time to First Inch (min)", "Night Shift Time to First Inch (min)"])].copy()
    _chart_inching_series(ttfi_df, title="Time to first inch", units="min")


def main() -> None:
    _card_css()
    project = st.session_state.session.project
    render_registered_page_header("analytics", chips=[project.name] if project is not None else ["Project required"])

    if project is None:
        st.info(":material/info: load a project to view available analytics.")
        st.stop()

    project_id = st.session_state.session.project.uuid
    st.session_state["project_id"] = project_id
    with st.popover(":material/knob: Controls"):
        
        st.caption("Limit analytics to a date window for burnup and events.")
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input("From", value=None)
        with col2:
            date_to = st.date_input("To", value=None)
        refresh = st.button("Refresh data", width="stretch")

    try:
        if refresh:
            _fetch_dashboard.clear()
            fetch_analytics.clear()
        dashboard = _fetch_dashboard(project_id, date_from, date_to)
    except Exception as exc:
        st.error(f"Failed to load analytics: {exc}")
        return

    _render_project_header(dashboard)
    st.write("")
    _render_overview_kpis(dashboard)
    st.write("")

    tab_progress, tab_breakdowns, tab_normalized, tab_inching = st.tabs(
        ["Progress", "Breakdowns", "Normalized", "Inching"]
    )
    with tab_progress:
        _render_progress_tab(dashboard)
    with tab_breakdowns:
        _render_breakdowns_tab(dashboard)
    with tab_normalized:
        _render_normalized_tab(project_id, refresh)
    with tab_inching:
        _render_inching_tab(project_id, date_from, date_to, refresh)


main()
