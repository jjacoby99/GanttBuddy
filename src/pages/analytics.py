from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
import altair as alt

from models.task import TaskType

from logic.backend.api_client import fetch_analytics, fetch_inching_performance
from ui.utils.phase_delay_plot import generate_phase_delay_plot

# -------------------------
# Config
# -------------------------
st.set_page_config(page_title="Analytics", layout="wide")


# -------------------------
# Small UI helpers
# -------------------------
def _fmt_num(x: Any, *, decimals: int = 2) -> str:
    if x is None:
        return "—"
    try:
        if isinstance(x, (int,)) and decimals == 0:
            return f"{x:,}"
        v = float(x)
        if math.isfinite(v):
            return f"{v:,.{decimals}f}"
    except Exception:
        pass
    return str(x)


def _fmt_pct(x: Any, *, decimals: int = 1) -> str:
    if x is None:
        return "—"
    try:
        v = float(x)
        return f"{v:.{decimals}f}%"
    except Exception:
        return str(x)


def _normalize_task_type(s: str) -> str:
    # "TaskType.INCH" -> "INCH"
    if not s:
        return "UNKNOWN"
    return s.split(".")[-1]


def _safe_get(d: Dict[str, Any], *path: str, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def _kpi_lookup(kpis: List[dict]) -> Dict[str, dict]:
    return {k["key"]: k for k in (kpis or [])}


def _card_css():
    st.markdown(
        """
        <style>
        .gb-card {
            border: 1px solid rgba(49, 51, 63, 0.15);
            border-radius: 16px;
            padding: 16px 16px 12px 16px;
            background: white;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }
        .gb-title {
            font-size: 14px;
            color: rgba(49, 51, 63, 0.70);
            margin-bottom: 6px;
            font-weight: 600;
        }
        .gb-value {
            font-size: 28px;
            font-weight: 800;
            line-height: 1.1;
            color: rgba(49, 51, 63, 0.95);
        }
        .gb-sub {
            margin-top: 6px;
            font-size: 12px;
            color: rgba(49, 51, 63, 0.65);
        }
        .gb-pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            margin-left: 8px;
        }
        .pill-good { background: rgba(0, 200, 0, 0.10); color: rgba(0, 110, 0, 0.95); }
        .pill-bad  { background: rgba(255, 0, 0, 0.10); color: rgba(150, 0, 0, 0.95); }
        .pill-neutral { background: rgba(144, 213, 255, 1); color: rgba(49, 51, 63, 0.75); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _kpi_card(title: str, value: str, subtitle: str = "", pill: Optional[Tuple[str, str]] = None):
    pill_html = ""
    if pill:
        pill_text, pill_class = pill
        pill_html = f'<span class="gb-pill {pill_class}">{pill_text}</span>'
    st.markdown(
        f"""
        <div class="gb-card">
          <div class="gb-title">{title}</div>
          <div class="gb-value">{value}</div>
          <div class="gb-sub">{subtitle}</div>
          <div class="gb-pill">{pill_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------
# Data transforms
# -------------------------
def df_burnup(dashboard: dict) -> pd.DataFrame:
    planned = _safe_get(dashboard, "burnup", "cumulative_planned_hours", default=[]) or []
    actual = _safe_get(dashboard, "burnup", "cumulative_actual_hours", default=[]) or []

    dfp = pd.DataFrame(planned)
    dfa = pd.DataFrame(actual)

    if dfp.empty and dfa.empty:
        return pd.DataFrame(columns=["x", "series", "y"])

    if not dfp.empty:
        dfp["series"] = "Planned"
    if not dfa.empty:
        dfa["series"] = "Actual"

    df = pd.concat([dfp, dfa], ignore_index=True)
    df["x"] = pd.to_datetime(df["x"]).dt.date
    df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0.0)
    return df.sort_values(["x", "series"])


def df_by_phase(dashboard: dict) -> pd.DataFrame:
    rows = _safe_get(dashboard, "by_phase", "rows", default=[]) or []
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(
            columns=["phase_name", "task_count", "planned_hours", "actual_hours", "delta_hours", "pct_complete"]
        )

    # Temporary de-dupe/group by name (because you currently have duplicates).
    df["phase_name"] = df["phase_name"].astype(str)
    for col in ["task_count", "planned_hours", "actual_hours", "delta_hours", "pct_complete"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    g = df.groupby("phase_name", as_index=False).agg(
        task_count=("task_count", "sum"),
        planned_hours=("planned_hours", "sum"),
        actual_hours=("actual_hours", "sum"),
    )
    g["delta_hours"] = g["actual_hours"] - g["planned_hours"]
    # pct_complete weighted by planned hours (better than averaging)
    # If planned_hours is 0, fallback to simple average.
    df["planned_hours_nonzero"] = df["planned_hours"].replace({0: float("nan")})
    weighted = (
        df.assign(w=df["planned_hours_nonzero"])
        .groupby("phase_name")
        .apply(lambda x: (x["pct_complete"] * x["planned_hours"]).sum() / max(x["planned_hours"].sum(), 1e-9))
    )
    g = g.merge(weighted.rename("pct_complete"), left_on="phase_name", right_index=True, how="left")
    g["pct_complete"] = g["pct_complete"].fillna(
        df.groupby("phase_name")["pct_complete"].mean()
    )

    return g.sort_values("planned_hours", ascending=False)


def df_by_task_type(dashboard: dict) -> pd.DataFrame:
    rows = _safe_get(dashboard, "by_task_type", "rows", default=[]) or []
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["task_type", "task_count", "planned_hours", "actual_hours", "delta_hours"])

    df["task_type"] = df["task_type"].astype(str).map(_normalize_task_type)
    for col in ["task_count", "planned_hours", "actual_hours"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["delta_hours"] = df["actual_hours"] - df["planned_hours"]
    return df.sort_values("planned_hours", ascending=False)


def df_events(dashboard: dict) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # overview events_by_type
    evt = _safe_get(dashboard, "overview", "events_by_type", default=[]) or []
    df_by_type = pd.DataFrame(evt)
    if not df_by_type.empty:
        df_by_type["count"] = pd.to_numeric(df_by_type["count"], errors="coerce").fillna(0).astype(int)

    # timeline
    series = _safe_get(dashboard, "events_timeline", "series", default=[]) or []
    rows = []
    for s in series:
        name = s.get("name", "UNKNOWN")
        for p in s.get("points", []) or []:
            rows.append({"event_type": name, "x": p.get("x"), "y": p.get("y", 0)})
    df_timeline = pd.DataFrame(rows)
    if not df_timeline.empty:
        df_timeline["x"] = pd.to_datetime(df_timeline["x"]).dt.date
        df_timeline["y"] = pd.to_numeric(df_timeline["y"], errors="coerce").fillna(0.0)

    return df_by_type, df_timeline


# -------------------------
# Charts
# -------------------------
def chart_burnup(df: pd.DataFrame):
    if df.empty:
        st.info("No burnup data yet.")
        return

    base = alt.Chart(df).encode(
        x=alt.X("x:T", title=None),
        y=alt.Y("y:Q", title="Cumulative Hours"),
        tooltip=[alt.Tooltip("x:T", title="Date"), alt.Tooltip("series:N"), alt.Tooltip("y:Q", format=",.2f")],
    )

    line = base.mark_line(point=True).encode(color=alt.Color("series:N", title=None))
    st.altair_chart(line.properties(height=320), width="stretch")


def chart_phase_delta(df: pd.DataFrame):
    if df.empty:
        st.info("No phase data yet.")
        return

    top = df.head(12).copy()
    top["delta_hours"] = top["delta_hours"].round(2)

    c = (
        alt.Chart(top)
        .mark_bar()
        .encode(
            y=alt.Y("phase_name:N", sort="-x", title=None),
            x=alt.X("delta_hours:Q", title="Delta Hours (Actual - Planned)"),
            tooltip=[
                alt.Tooltip("phase_name:N", title="Phase"),
                alt.Tooltip("planned_hours:Q", format=",.2f", title="Planned (h)"),
                alt.Tooltip("actual_hours:Q", format=",.2f", title="Actual (h)"),
                alt.Tooltip("delta_hours:Q", format=",.2f", title="Delta (h)"),
                alt.Tooltip("pct_complete:Q", format=".0%", title="% Complete"),
            ],
        )
    )
    st.altair_chart(c.properties(height=380), width="stretch")


def chart_task_type_hours(df: pd.DataFrame):
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

    c = (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            x=alt.X("task_type:N", sort="-y", title=None),
            y=alt.Y("hours:Q", title="Hours"),
            xOffset="series:N",
            color=alt.Color("series:N", title=None),
            tooltip=[
                alt.Tooltip("task_type:N", title="Task Type"),
                alt.Tooltip("series:N"),
                alt.Tooltip("hours:Q", format=",.2f"),
            ],
        )
    )
    st.altair_chart(c.properties(height=320), width="stretch")


def chart_events_timeline(df: pd.DataFrame):
    if df.empty:
        st.info("No event timeline data yet.")
        return

    c = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("x:T", title=None),
            y=alt.Y("y:Q", title="Events"),
            color=alt.Color("event_type:N", title=None),
            tooltip=[alt.Tooltip("x:T", title="Date"), alt.Tooltip("event_type:N"), alt.Tooltip("y:Q")],
        )
    )
    st.altair_chart(c.properties(height=260), width="stretch")

def _kpi_value(kpis: list[dict], key: str):
    for k in kpis or []:
        if k.get("key") == key:
            return k.get("value"), k.get("unit")
    return None, None


def df_inching_shift_rows(payload: dict) -> pd.DataFrame:
    rows = payload.get("shift_inch_performance") or []
    flat = []
    for r in rows:
        base = {
            "crew": r.get("crew_name", "—"),
            "shift_type": (r.get("shift_type") or "").split(".")[-1],
            "shift_date": r.get("shift_date"),
        }
        kpis = r.get("kpis") or []
        for key in ("avg_inch_time", "min_inch_time", "max_inch_time", "inch_count"):
            base[key] = next((k.get("value") for k in kpis if k.get("key") == key), None)
        flat.append(base)

    df = pd.DataFrame(flat)
    if df.empty:
        return pd.DataFrame(columns=["shift_date", "shift_type", "crew", "avg_inch_time", "min_inch_time", "max_inch_time", "inch_count"])

    df["shift_date"] = pd.to_datetime(df["shift_date"]).dt.date
    for c in ["avg_inch_time", "min_inch_time", "max_inch_time"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["inch_count"] = pd.to_numeric(df["inch_count"], errors="coerce").fillna(0).astype(int)
    return df.sort_values(["shift_date", "shift_type", "crew"])

from typing import Literal

def df_inching_series(payload: dict, start_dt: Optional[datetime] = None) -> pd.DataFrame:
    # payload.series: list[{name, points:[{x(date), y(float)}]}]
    series = payload.get("series") or []
    rows = []
    for s in series:
        name = s.get("name", "Series")
        for p in s.get("points") or []:
            rows.append({"series": name, "x": p.get("x"), "y": p.get("y")})

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=["x", "series", "y"])

    df["x"] = pd.to_datetime(df["x"]).dt.date
    
    if start_dt and isinstance(start_dt, datetime):
        df = df[df["x"] >= start_dt.date()]

    return df.sort_values(["x", "series"])


def chart_inching_series(df: pd.DataFrame, stat_name: str = "Avg Inch time", units: Literal["mins", "hours"] = "mins"):
    if df.empty:
        st.info("No inching timeseries data yet.")
        return

    c = (
        alt.Chart(df)
        .mark_line(point=True)
        .encode(
            x=alt.X("x:T", title="Date"),
            y=alt.Y("y:Q", title=f"{stat_name} ({units})"),
            color=alt.Color("series:N", title=None),
            tooltip=[
                alt.Tooltip("x:T", title="Date"),
                alt.Tooltip("series:N", title="Series"),
                alt.Tooltip("y:Q", title=f"{stat_name} ({units})", format=",.2f"),
            ],
        )
    )
    st.altair_chart(c, width="stretch")

import altair as alt
import pandas as pd
import streamlit as st

def chart_avg_inch_time_by_shift_over_time(df: pd.DataFrame):
    if df.empty:
        st.info("No shift inching performance rows yet.")
        return

    d = df.copy()
    d["shift_date"] = pd.to_datetime(d["shift_date"])
    # bucket to day so the x-axis is clean
    d["shift_day"] = d["shift_date"].dt.floor("D")

    c = (
        alt.Chart(d)
        .transform_aggregate(
            mean_avg_inch_time="mean(avg_inch_time)",
            groupby=["shift_type", "shift_day"],
        )
        .mark_line(point=True)
        .encode(
            x=alt.X("shift_day:T", title="Date"),
            y=alt.Y("mean_avg_inch_time:Q", title="Avg inch time (min)"),
            color=alt.Color("shift_type:N", title="Shift", sort=["day", "night"]),
            tooltip=[
                alt.Tooltip("shift_day:T", title="Date"),
                alt.Tooltip("shift_type:N", title="Shift"),
                alt.Tooltip("mean_avg_inch_time:Q", title="Avg (min)", format=",.2f"),
            ],
        )
        .properties(height=320)
        .configure_view(stroke=None)
    )

    st.altair_chart(c, width="stretch") # test

def chart_inching_shift_bars(df: pd.DataFrame):
    if df.empty:
        st.info("No shift inching performance rows yet.")
        return

    top = df.copy()

    # Normalize for consistent legend + consistent color mapping
    top["shift_type_norm"] = top["shift_type"].astype(str).str.strip().str.upper()
    top["shift_label"] = top["shift_type_norm"].map({"DAY": "Day", "NIGHT": "Night"}).fillna(top["shift_type_norm"])

    top["label"] = top["shift_date"].astype(str) + " · " + top["shift_label"]

    base = alt.Chart(top).encode(
        y=alt.Y("label:N", sort="-x", title=None, axis=alt.Axis(labelLimit=0)),
        x=alt.X("avg_inch_time:Q", title="Avg inch time (min)"),
        color=alt.Color(
            "shift_label:N",
            title="Shift",
            # lock ordering so "Day" / "Night" are stable in the legend and colors
            sort=["Day", "Night"],
        ),
        tooltip=[
            alt.Tooltip("shift_date:T", title="Shift date"),
            alt.Tooltip("shift_label:N", title="Shift"),
            alt.Tooltip("crew:N", title="Crew"),
            alt.Tooltip("avg_inch_time:Q", title="Avg (min)", format=",.2f"),
            alt.Tooltip("min_inch_time:Q", title="Fastest (min)", format=",.2f"),
            alt.Tooltip("max_inch_time:Q", title="Slowest (min)", format=",.2f"),
            alt.Tooltip("inch_count:Q", title="Count"),
        ],
    )

    bars = base.mark_bar()

    labels = base.mark_text(
        align="left",
        dx=6,  # push text a bit right of the bar end
    ).encode(
        text=alt.Text("avg_inch_time:Q", format=",.1f")
    )

    c = (bars + labels).properties(height=alt.Step(24))
    st.altair_chart(c, width="stretch")

# -------------------------
# Page
# -------------------------
#@st.cache_data(ttl=30, show_spinner=False)
def fetch_inching(project_id: str, date_from: Optional[date], date_to: Optional[date]) -> dict:
    headers = st.session_state.get("auth_headers", {})
    pid = st.session_state.get("project_id") or st.session_state.session.project.uuid
    return fetch_inching_performance(
        headers=headers,
        project_id=pid,
        date_from=date_from,
        date_to=date_to,
    )


@st.cache_data(ttl=30, show_spinner=False)
def fetch_dashboard(project_id: str, date_from: Optional[date], date_to: Optional[date]) -> dict:
    params = {}
    
    headers = st.session_state.get("auth_headers", {})
    pid = st.session_state.get("project_id") or st.session_state.session.project.uuid 
    return fetch_analytics(
        headers=headers,
        project_id=pid,
        date_from=date_from,
        date_to=date_to,
    )


def main():
    _card_css()

    st.title("Analytics")

    # Sidebar controls
    with st.sidebar:
        st.subheader("Controls")
        project_id = st.text_input(
            "Project ID", 
            value=st.session_state.session.project.uuid
        )
        st.session_state["project_id"] = project_id

        st.caption("Optional: limit analytics to a date window (burnup + events).")
        col_a, col_b = st.columns(2)
        with col_a:
            date_from = st.date_input("From", value=None)
        with col_b:
            date_to = st.date_input("To", value=None)

        refresh = st.button("Refresh data", width="stretch")

    if not project_id:
        st.info("Enter a Project ID in the sidebar to view analytics.")
        return

    try:
        if refresh:
            fetch_dashboard.clear()
        dash = fetch_dashboard(project_id, date_from, date_to)
    except Exception as e:
        st.error(f"Failed to load analytics: {e}")
        return

    meta = dash.get("metadata") or {}
    as_of = dash.get("as_of")
    # Header: project context
    left, right = st.columns([2, 1])
    with left:
        st.markdown(
            f"""
            <div class="gb-card">
              <div class="gb-title">Project</div>
              <div class="gb-value" style="font-size:22px;">
                {meta.get("site_name", "—")} · {meta.get("mill_name", "—")}
              </div>
              <div class="gb-sub">
                Vendor: <b>{meta.get("vendor","—")}</b> · System: <b>{meta.get("liner_system","—")}</b>
                · Scope: <b>{meta.get("scope","—")}</b> · Campaign: <b>{meta.get("campaign_id","—")}</b>
              </div>
              <div class="gb-sub">Supervisor: <b>{meta.get("supervisor","—")}</b> · As of: {as_of or "—"}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        notes = (meta.get("notes") or "").strip()
        if notes:
            st.markdown(
                f"""
                <div class="gb-card">
                  <div class="gb-title">Notes</div>
                  <div style="font-size:14px; color: rgba(49,51,63,0.85); line-height:1.4;">
                    {notes}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="gb-card">
                  <div class="gb-title">Notes</div>
                  <div class="gb-sub">No notes provided.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")

    # KPIs
    overview = dash.get("overview", {})
    kpis = _kpi_lookup(overview.get("kpis", []))
    task_counts = overview.get("task_counts", {}) or {}

    task_count = kpis.get("task_count", {}).get("value")
    planned_h = kpis.get("planned_hours", {}).get("value")
    actual_h = kpis.get("actual_hours", {}).get("value")
    delta_h = kpis.get("delta_hours", {}).get("value")
    pct_complete = kpis.get("pct_complete", {}).get("value")

    # sentiment pill for delta
    pill = None
    try:
        d = float(delta_h)
        if d < -0.01:
            pill = ("Under plan", "pill-good")
        elif d > 0.01:
            pill = ("Over plan", "pill-bad")
        else:
            pill = ("On plan", "pill-neutral")
    except Exception:
        pill = None

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        _kpi_card("Tasks", _fmt_num(task_count, decimals=0), f"Done: {task_counts.get('done','—')} · Remaining: {task_counts.get('not_done','—')}")
    with c2:
        _kpi_card("Planned Hours", f"{_fmt_num(planned_h)} h", f"Planned tasks: {task_counts.get('planned','—')}")
    with c3:
        _kpi_card("Actual Hours", f"{_fmt_num(actual_h)} h", f"Unplanned tasks: {task_counts.get('unplanned','—')}")
    with c4:
        _kpi_card("Delta (A - P)", f"{_fmt_num(delta_h)} h", "Negative is good", pill=pill)
    with c5:
        _kpi_card("Complete", _fmt_pct(pct_complete), "Based on task completion")

    st.write("")

    # Main visuals: burnup + breakdowns
    tab1, tab2, tab3 = st.tabs(["Progress", "Breakdowns", "Inching"])
    with tab1:

        plot_col, metrics_col = st.columns([5,1])
        
        with plot_col:
            st.subheader("Progress vs Plan")
            df_bu = df_burnup(dash)
            chart_burnup(df_bu)

            # quick stats beneath the chart
            if not df_bu.empty:
                latest = df_bu.sort_values("x").groupby("series").tail(1).set_index("series")
                p_end = float(latest.loc["Planned", "y"]) if "Planned" in latest.index else None
                a_end = float(latest.loc["Actual", "y"]) if "Actual" in latest.index else None
                if p_end is not None and a_end is not None:
                    gap = a_end - p_end
                    st.caption(f"End-of-window actual minus planned: {_fmt_num(gap)} h")
        
        with metrics_col:
            _kpi_card("Planned Hours", f"{_fmt_num(planned_h)} h", f"Planned tasks: {task_counts.get('planned','—')}")
            st.space("small")
            _kpi_card("Actual Hours", f"{_fmt_num(actual_h)} h", f"Unplanned tasks: {task_counts.get('unplanned','—')}")
            st.space("small")
            _kpi_card("Variance", f"{_fmt_num(delta_h)} h", "Negative is good", pill=pill)
    
    with tab2:
        left, right = st.columns([2, 1])

        with left:
            st.subheader("By Phase")
            df_ph = df_by_phase(dash)
            
            # highlight top contributors
            fig = generate_phase_delay_plot(project=st.session_state.session.project, units="hours")
            st.plotly_chart(fig, width="stretch")

        with right:
            st.space("large")
            st.space("medium")
            if df_ph.empty:
                st.info("No phase data yet.")
            else:
                show = df_ph.copy()
                show["pct_complete"] = (show["pct_complete"] * 100.0).round(1)
                show = show.rename(
                    columns={
                        "phase_name": "Phase",
                        "task_count": "Tasks",
                        "planned_hours": "Planned (h)",
                        "actual_hours": "Actual (h)",
                        "delta_hours": "Delta (h)",
                        "pct_complete": "Complete (%)",
                    }
                )
                st.dataframe(
                    show,
                    width="stretch",
                    hide_index=True,
                )

        st.write("")
        st.divider()

        st.subheader("By Task Type")
        df_tt = df_by_task_type(dash)

        # If your db is still corrupt, call it out so you don't fool yourself.
        if not df_tt.empty:
            generic_row = df_tt[df_tt["task_type"] == "GENERIC"]
            if not generic_row.empty:
                frac = float(generic_row["task_count"].iloc[0]) / max(float(df_tt["task_count"].sum()), 1.0)
                if frac > 0.6:
                    st.warning(
                        f"Task type data looks dominated by GENERIC ({frac:.0%} of tasks). "
                    )

        chart_task_type_hours(df_tt)

        if not df_tt.empty:
            # compact table
            tshow = df_tt.rename(
                columns={
                    "task_type": "Task Type",
                    "task_count": "Tasks",
                    "planned_hours": "Planned (h)",
                    "actual_hours": "Actual (h)",
                    "delta_hours": "Delta (h)",
                }
            ).copy()
            tshow["Planned (h)"] = tshow["Planned (h)"].round(2)
            tshow["Actual (h)"] = tshow["Actual (h)"].round(2)
            tshow["Delta (h)"] = tshow["Delta (h)"].round(2)
            st.dataframe(tshow, width="stretch", hide_index=True)


    with tab3:
        st.subheader("Inching Performance")

        try:
            if refresh:
                fetch_inching.clear()
            inch = fetch_inching(project_id, date_from, date_to)
        except Exception as e:
            st.error(f"Failed to load inching performance: {e}")
            return

        if not inch or (not inch.get("kpis") and not inch.get("shift_inch_performance")):
            st.info("No inching data available (no INCH tasks, or no actuals yet).")
            return

        # --- KPI strip ---
        ikpis = inch.get("kpis") or []

        p_avg, _ = _kpi_value(ikpis, "Project_avg")
        p_min, _ = _kpi_value(ikpis, "Project_min")
        p_max, _ = _kpi_value(ikpis, "Project_max")
        p_cnt, _ = _kpi_value(ikpis, "Project_count")

        d_avg, _ = _kpi_value(ikpis, "Day shift_avg")
        n_avg, _ = _kpi_value(ikpis, "Night shift_avg")

        
        # --- Timeseries: avg per shift-date (day/night) ---
        plot_col, metrics_col = st.columns([3,1])
        with plot_col:
            st.markdown("**Avg inch time by date**")
            ttfi_cutoff = st.session_state.session.project.first_ttfi_cutoff
            df_is_raw = df_inching_series(inch, start_dt=ttfi_cutoff)
            df_is_filtered = df_is_raw[df_is_raw['series'].isin(["Day shift avg inch time (min)", "Night shift avg inch time (min)"])].copy()

            ttfi_cols = ["Day Shift Time to First Inch (min)", "Night Shift Time to First Inch (min)"]
            df_ttfi_filtered = df_is_raw[df_is_raw['series'].isin(ttfi_cols)].copy()
            
            chart_inching_series(df_is_filtered, units="mins")
            

        with metrics_col:
            c1, c2 = st.columns(2)

            # compare fastest vs slowest
            diff_pill = None
            try:
                if p_min is not None and p_max is not None:
                    gap = p_max - p_min
                    if gap > 0.01:
                        diff_pill = (f"{_fmt_num(gap)} min gap", "pill-bad")
                    else:
                        diff_pill = ("Similar", "pill-neutral")
            except Exception:
                pass
            
            avg_inch_pill = None
            avg_planned_inch = st.session_state.session.project.average_planned_duration(TaskType.INCH)
            if avg_planned_inch > p_avg:
                # faster than planned is good
                avg_inch_pill = (f"Planned: {_fmt_num(avg_planned_inch*60)} min", "pill-good")
            elif abs(avg_planned_inch - p_avg) < 0.01:
                avg_inch_pill = ("On par with planned", "pill-neutral")
            else:
                avg_inch_pill = (f"Planned: {_fmt_num(avg_planned_inch*60)} min", "pill-bad")

            with c1.container():
                _kpi_card("Project Avg", f"{_fmt_num(p_avg)} min", "All Inch tasks", pill=avg_inch_pill)
                st.space("stretch")
                _kpi_card("Fastest vs Slowest", f"{_fmt_num(p_min)} / {_fmt_num(p_max)} min", f"{_fmt_num(p_max - p_min)} min gap", pill=diff_pill)
            
            
            # quick compare pill day vs night avg
            pill = None
            try:
                dv = float(d_avg) if d_avg is not None else None
                nv = float(n_avg) if n_avg is not None else None
                if dv is not None and nv is not None:
                    if dv < nv - 0.01:
                        pill = (f"Day {_fmt_num(nv - dv)} min faster", "pill-neutral")
                    elif dv > nv + 0.01:
                        pill = (f"Night {_fmt_num(dv - nv)} min faster", "pill-neutral")
                    else:
                        pill = ("Similar", "pill-neutral")
            except Exception:
                pill = None

            with c2.container():
                _kpi_card("Count", _fmt_num(p_cnt, decimals=0), "Inches completed")
                st.space("stretch")
                _kpi_card("Day vs Night Avg", f"{_fmt_num(d_avg)} / {_fmt_num(n_avg)} min", "Avg inch time", pill=pill)
        
        st.write("")

        st.divider()
        
        st.markdown("**Time to First Inch: Day vs. Night**")
        
        met_col_2, plot_col_2 = st.columns([1,3])
        with met_col_2:
            ft_avg_day, _ = _kpi_value(ikpis, "Day Shift Time to First Inch_avg")
            ft_avg_night, _ = _kpi_value(ikpis, "Night Shift Time to First Inch_avg")
            
            ft_min_day, _ = _kpi_value(ikpis, "Day Shift Time to First Inch_min")
            ft_min_night, _ = _kpi_value(ikpis, "Night Shift Time to First Inch_min")

            ft_max_day, _ = _kpi_value(ikpis, "Day Shift Time to First Inch_max")
            ft_max_night, _ = _kpi_value(ikpis, "Night Shift Time to First Inch_max")

            def generate_day_night_pill(day_val, night_val):
                try:
                    dv = float(day_val) if day_val is not None else None
                    nv = float(night_val) if night_val is not None else None
                    if dv is not None and nv is not None:
                        if dv < nv - 0.01:
                            return (f"Day {_fmt_num(nv - dv)} min faster", "pill-neutral")
                        elif dv > nv + 0.01:
                            return (f"Night {_fmt_num(dv - nv)} min faster", "pill-neutral")
                        else:
                            return ("Similar", "pill-neutral")
                except Exception:
                    pass
                return None
            
            avg_ttfi_pill = generate_day_night_pill(ft_avg_day, ft_avg_night)
            

            fastest_ttfi_pill = generate_day_night_pill(ft_min_day, ft_min_night)
            
            slowest_ttfi_pill = generate_day_night_pill(ft_max_day, ft_max_night)
            
            c1, c2 = st.columns(2)
            with c1:
                _kpi_card("Average", f"{_fmt_num(ft_avg_day)} / {_fmt_num(ft_avg_night)} min", "Day / Night shifts", pill=avg_ttfi_pill)
            with c2:
                _kpi_card("Fastest", f"{_fmt_num(ft_min_day)} / {_fmt_num(ft_min_night)} min", f"Day / Night shifts", pill=fastest_ttfi_pill)
                st.space("small")
                _kpi_card("Slowest", f"{_fmt_num(ft_max_day)} / {_fmt_num(ft_max_night)} min", f"Day / Night shifts", pill=slowest_ttfi_pill)
        
        
        with plot_col_2:
            chart_inching_series(df_ttfi_filtered, stat_name="Time to First Inch", units="mins")

        st.divider()

        # --- Shift-level breakdown ---
        st.markdown("**Shift-by-shift performance**")
        df_ir = df_inching_shift_rows(inch)

        # Filter controls
        with st.popover('Filter'):
            shift_filter = st.multiselect("Shift", options=["DAY", "NIGHT"], default=["DAY", "NIGHT"])
            crews = sorted([c for c in df_ir["crew"].dropna().unique().tolist()]) if not df_ir.empty else []
            crew_filter = st.multiselect("Crew", options=crews, default=crews[:10] if len(crews) > 10 else crews)
            sort_mode = st.selectbox("Sort", ["Most recent", "Slowest avg", "Fastest avg"], index=0)

        view = df_ir.copy()
        if shift_filter:
            view = view[view["shift_type"].isin(shift_filter)]
        if crew_filter:
            view = view[view["crew"].isin(crew_filter)]

        if sort_mode == "Most recent":
            view = view.sort_values(["shift_date"], ascending=False)
        elif sort_mode == "Slowest avg":
            view = view.sort_values(["avg_inch_time"], ascending=False)
        else:
            view = view.sort_values(["avg_inch_time"], ascending=True)

        if view.empty:
            st.info("No shift rows match your filters.")
        else:
            # chart + table
            chart_inching_shift_bars(view.head(25))

        if df_ir.empty:
            st.info("No shift inching performance rows yet.")
        else:
            show = df_ir.rename(
                columns={
                    "shift_date": "Shift Date",
                    "shift_type": "Shift",
                    "crew": "Crew",
                    "avg_inch_time": "Avg (min)",
                    "min_inch_time": "Fastest (min)",
                    "max_inch_time": "Slowest (min)",
                    "inch_count": "Count",
                }
            ).copy()

            for c in ["Avg (min)", "Fastest (min)", "Slowest (min)"]:
                show[c] = pd.to_numeric(show[c], errors="coerce").round(2)

            st.dataframe(show, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()