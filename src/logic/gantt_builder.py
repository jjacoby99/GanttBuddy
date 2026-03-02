from __future__ import annotations
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

import streamlit as st
from streamlit import cache_data

from logic.plot_utilities import adjust_color_any
from plotly.colors import qualitative as q

from models.project import Project
from models.gantt_models import GanttInputs
from models.gantt_state import GanttState

# -----------------------------
# Label formatting helpers
# -----------------------------

import datetime as dt
from typing import Iterable, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def _fmt_dt_local_naive(x: dt.datetime) -> str:
    # Assumes x is already in the same "wall clock" basis as the Gantt.
    return x.strftime("%Y-%m-%d %H:%M")


def _fmt_minutes(mins: int) -> str:
    mins = int(mins)
    h, m = divmod(mins, 60)
    if h <= 0:
        return f"{m}m"
    return f"{h}h {m}m"


def _normalize_delay_type(x) -> str:
    # DelayType enum or string
    if x is None:
        return "OTHER"
    return getattr(x, "value", str(x))


def _prep_delay_windows(
    rows: list,
    *,
    allowed_types: Optional[set[str]] = None,
) -> tuple[tuple[str, str, dt.datetime, dt.datetime, int, str], ...]:
    """
    Returns hashable delay windows for caching.
    Tuple shape:
      (key, delay_type, start_dt, end_dt, duration_minutes, description)
    """
    out: list[tuple[str, str, dt.datetime, dt.datetime, int, str]] = []

    for r in rows or []:
        delay_type = _normalize_delay_type(getattr(r, "delay_type", None))
        if allowed_types is not None and delay_type not in allowed_types:
            continue

        desc = (getattr(r, "description", "") or "").strip()
        dur = int(getattr(r, "duration_minutes", 0) or 0)

        start = getattr(r, "start_dt", None)
        end = getattr(r, "end_dt", None)

        if start is None and end is None:
            continue

        if start is not None and end is None and dur > 0:
            end = start + dt.timedelta(minutes=dur)
        elif end is not None and start is None and dur > 0:
            start = end - dt.timedelta(minutes=dur)

        if start is None or end is None:
            continue

        # Ensure ordering
        if end < start:
            start, end = end, start

        key = str(getattr(r, "id", None) or getattr(r, "client_id", None) or f"{delay_type}:{start}:{end}")
        out.append((key, delay_type, start, end, dur, desc))

    # Stable ordering helps cache + deterministic rendering
    out.sort(key=lambda t: (t[2], t[3], t[1], t[0]))
    return tuple(out)


def _pick_overlap_df(df: pd.DataFrame, show_actual: bool) -> pd.DataFrame:
    tasks = df[df["Level"] == "Task"].copy()
    if tasks.empty:
        return tasks

    if show_actual and (tasks["Type"] == "Actual").any():
        tasks = tasks[tasks["Type"] == "Actual"]
        if not tasks.empty:
            return tasks

    return tasks[tasks["Type"] == "Planned"]


def _overlap_summary(tasks_df: pd.DataFrame, start: dt.datetime, end: dt.datetime) -> str:
    if tasks_df is None or tasks_df.empty:
        return "No tasks in current view"

    overlaps = tasks_df[(tasks_df["Start"] < end) & (tasks_df["Finish"] > start)]
    if overlaps.empty:
        return "No overlapping tasks in current view"

    labels = (
        overlaps["Label"]
        .dropna()
        .astype(str)
        .map(lambda s: s.strip())
        .tolist()
    )
    # de-dupe preserving order
    labels = list(dict.fromkeys([x for x in labels if x]))

    n = len(labels)
    head = labels[:6]
    tail = "" if n <= 6 else f" (+{n - 6} more)"
    return f"{n} tasks: {', '.join(head)}{tail}"


def _add_delay_overlays(
    *,
    fig: go.Figure,
    df: pd.DataFrame,
    delay_windows: tuple[tuple[str, str, dt.datetime, dt.datetime, int, str], ...],
    x_range: list,
    show_actual: bool,
) -> None:
    if not delay_windows:
        return

    # Hidden y-axis for "pins" at top of chart (avoids messing with categorical y)
    fig.update_layout(
        yaxis2=dict(
            overlaying="y",
            anchor="x",
            range=[0.0, 1.0],
            visible=False,
        )
    )

    # Color per delay type (light, translucent bands)
    types = sorted({t[1] for t in delay_windows})
    palette = px.colors.qualitative.G10
    type_color = {typ: palette[i % len(palette)] for i, typ in enumerate(types)}

    x0, x1 = x_range[0], x_range[1]

    tasks_df = _pick_overlap_df(df, show_actual=show_actual)

    # Add background bands (shapes)
    for _, typ, start, end, _, _ in delay_windows:
        # Skip windows completely outside current view
        if end <= x0 or start >= x1:
            continue

        fig.add_vrect(
            x0=max(start, x0),
            x1=min(end, x1),
            fillcolor=type_color.get(typ, "rgba(0,0,0,0.12)"),
            opacity=0.18,
            layer="below",
            line_width=1,
            line_dash="dot",
        )

    # Add hover "pins" grouped by type (one trace per type)
    by_type: dict[str, list[tuple[dt.datetime, list[str]]]] = {}
    for _, typ, start, end, dur, desc in delay_windows:
        if end <= x0 or start >= x1:
            continue

        mid = start + (end - start) / 2
        impacted = _overlap_summary(tasks_df, start, end)

        cd = [
            typ,
            desc if desc else "(no description)",
            _fmt_dt_local_naive(start),
            _fmt_dt_local_naive(end),
            _fmt_minutes(int((end - start).total_seconds() // 60) if (end and start) else dur),
            impacted,
        ]
        by_type.setdefault(typ, []).append((mid, cd))

    for typ, points in by_type.items():
        xs = [p[0] for p in points]
        customdata = [p[1] for p in points]

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=[0.985] * len(xs),
                yaxis="y2",
                mode="markers",
                name=f"Delay: {typ}",
                legendgroup=f"delay_{typ}",
                showlegend=True,
                marker=dict(
                    size=10,
                    symbol="triangle-down",
                ),
                customdata=np.array(customdata, dtype=object),
                hovertemplate = "<br>".join([
                    "<b>Delay</b>: %{customdata[0]}",
                    "<b>Description</b>: %{customdata[1]}",
                    "<b>Start</b>: %{customdata[2]}",
                    "<b>End</b>: %{customdata[3]}",
                    "<b>Duration</b>: %{customdata[4]}",
                    "<b>Overlaps</b>: %{customdata[5]}",
                ]) + "<extra></extra>"
            )
        )

def compute_left_margin(tick_labels: list[str]) -> int:
    if not tick_labels:
        return 120
    max_len = max(len(s) for s in tick_labels)

    return int(min(520, max(140, 8 * max_len + 40)))

_BOLD_MAP = str.maketrans({
    **{chr(ord('A') + i): chr(0x1D400 + i) for i in range(26)},  # 𝐀..𝐙
    **{chr(ord('a') + i): chr(0x1D41A + i) for i in range(26)},  # 𝐚..𝐳
    **{chr(ord('0') + i): chr(0x1D7CE + i) for i in range(10)},  # 𝟎..𝟗
})

def _unicode_bold(s: str) -> str:
    # "Bold-ish" axis labels without relying on HTML in tick text
    return (s or "").translate(_BOLD_MAP)

def _indent_task(name: str) -> str:
    # Visible hierarchy in the y-axis
    # (Box drawing chars render nicely in Plotly tick labels.)
    return f"   {name}"


def _format_duration(td, resolution: str = "hours") -> str:
    if td is None or pd.isna(td):
        return ""
    seconds = td.total_seconds()
    if resolution == "days":
        return f"{seconds / 86400:.2f} d"
    return f"{seconds / 3600:.2f} h"


# -----------------------------
# Your color map (kept)
# -----------------------------
def build_color_map(df: pd.DataFrame, planned_color: str, actual_color: str) -> dict[str, str]:
    """
    Semantic colors:
      - Planned bars are based on planned_color
      - Actual bars are based on actual_color
      - Phase vs Task are shade variations for hierarchy
    """
    if df is None or df.empty:
        return {}

    # tune these once and forget them
    # (idea: Phase a bit darker / heavier; Task a bit lighter / cleaner)
    def color_for(level: str, typ: str) -> str:
        base = planned_color if typ == "Planned" else actual_color

        if level == "Phase":
            # phase: darker / stronger
            return adjust_color_any(base, darken=0.20)
        else:
            # task: lighter
            return adjust_color_any(base, lighten=0.20)

    color_map: dict[str, str] = {}
    phases = df["Phase"].dropna().unique().tolist()
    for ph_name in phases:
        for level in ("Phase", "Task"):
            for typ in ("Planned", "Actual"):
                color_map[f"{ph_name}|{level}|{typ}"] = color_for(level, typ)

    return color_map


@cache_data
def build_gantt_df(project: Project, inputs: GanttState) -> pd.DataFrame | None:
    rows: list[dict] = []
    phases = project.phases

    phase_ids = getattr(project, "phase_order", list(phases.keys()))
    duration_resolution = getattr(project.settings, "duration_resolution", "hours")

    for ph_id in phase_ids:
        ph = phases[ph_id]

        # Planned phase row
        ph_start = getattr(ph, "start_date", None)
        ph_end   = getattr(ph, "end_date", None)
        rows.append({
            "RowID": f"PH:{ph_id}",
            "DisplayLabel": _unicode_bold(ph.name),
            "Label": ph.name,
            "Phase": ph.name,
            "PhaseID": ph_id,
            "Start": ph_start,
            "Finish": ph_end,
            "Level": "Phase",
            "Type": "Planned",
            "UUID": None,
            "TaskName": None,
            "Status": ph.status,
            "PlannedDuration": getattr(ph, "planned_duration", None),
            "ActualDuration": getattr(ph, "actual_duration", None),
            "Predecessors": [],
            "Note": None,
            "IsMilestone": False,
            "DurationResolution": duration_resolution,
        })

        # Actual phase row (only if both exist)
        astart = getattr(ph, "actual_start", None)
        aend   = getattr(ph, "actual_end", None)
        if inputs.show_actual and astart is not None and aend is not None:
            rows.append({
                "RowID": f"PH:{ph_id}",
                "DisplayLabel": _unicode_bold(ph.name),
                "Label": ph.name,
                "Phase": ph.name,
                "PhaseID": ph_id,
                "Start": astart,
                "Finish": aend,
                "Level": "Phase",
                "Type": "Actual",
                "UUID": None,
                "TaskName": None,
                "Status": ph.status,
                "PlannedDuration": getattr(ph, "planned_duration", None),
                "ActualDuration": getattr(ph, "actual_duration", None),
                "Predecessors": [],
                "Note": None,
                "IsMilestone": False,
                "DurationResolution": duration_resolution,
            })

        # Tasks
        task_ids = getattr(ph, "task_order", list(getattr(ph, "tasks", {}).keys()))
        for t_id in task_ids:
            t = ph.tasks[t_id]

            uuid = getattr(t, "uuid", None)
            preds = getattr(t, "predecessor_ids", None)
            preds = list(preds) if preds is not None else []

            planned_start = getattr(t, "start_date", None)
            planned_end   = getattr(t, "end_date", None)

            # milestone logic (prefer your property if it truly exists in your branch)
            is_ms = False
            if t.is_milestone:
                is_ms = bool(getattr(t, "is_milestone"))
            

            rows.append({
                "RowID": f"TK:{t_id}",
                "DisplayLabel": _indent_task(t.name),
                "Label": t.name,
                "TaskName": t.name,
                "Phase": ph.name,
                "PhaseID": ph_id,
                "Start": planned_start,
                "Finish": planned_end,
                "Level": "Task",
                "Type": "Planned",
                "UUID": uuid,
                "Status": getattr(t, "status", None),
                "PlannedDuration": getattr(t, "planned_duration", None),
                # Only show actual duration if COMPLETE / completed
                "ActualDuration": getattr(t, "actual_duration", None) if getattr(t, "completed", False) else None,
                "Predecessors": preds,
                "Note": getattr(t, "note", None),
                "IsMilestone": is_ms,
                "DurationResolution": duration_resolution,
            })

            # Actual task row (only if both exist)
            astart_t = getattr(t, "actual_start", None)
            aend_t   = getattr(t, "actual_end", None)
            if inputs.show_actual and astart_t is not None and aend_t is not None:
                rows.append({
                    "RowID": f"TK:{t_id}",
                    "DisplayLabel": _indent_task(t.name),
                    "Label": t.name,
                    "TaskName": t.name,
                    "Phase": ph.name,
                    "PhaseID": ph_id,
                    "Start": astart_t,
                    "Finish": aend_t,
                    "Level": "Task",
                    "Type": "Actual",
                    "UUID": uuid,
                    "Status": getattr(t, "status", None),
                    "PlannedDuration": getattr(t, "planned_duration", None),
                    "ActualDuration": getattr(t, "actual_duration", None) if getattr(t, "completed", False) else None,
                    "Predecessors": preds,
                    "Note": getattr(t, "note", None),
                    "IsMilestone": is_ms,
                    "DurationResolution": duration_resolution,
                })

    df = pd.DataFrame(rows)
    if df.empty:
        return None

    df = df[df["Start"].notna() & df["Finish"].notna()].copy()
    if df.empty:
        return None

    # Color key (same concept you had)
    df["ColorKey"] = df.apply(lambda r: f"{r['Phase']}|{r['Level']}|{r['Type']}", axis=1)

    df["Start_str"]  = pd.to_datetime(df["Start"]).dt.strftime("%Y-%m-%d %H:%M")
    df["Finish_str"] = pd.to_datetime(df["Finish"]).dt.strftime("%Y-%m-%d %H:%M")

    df["PlannedDur_str"] = df.apply(
        lambda r: _format_duration(r["PlannedDuration"], r["DurationResolution"]), axis=1
    )
    df["ActualDur_str"] = df.apply(
        lambda r: _format_duration(r["ActualDuration"], r["DurationResolution"]), axis=1
    )

    return df


def _apply_selection_styling(fig: go.Figure, selected_uuid: str | None) -> None:
    """
    Visually highlight the selected task:
      - Selected bar gets thicker outline
      - Non-selected bars are slightly dimmed
    This relies on UUID being present in customdata.
    """
    if not selected_uuid:
        # reset-ish defaults
        for tr in fig.data:
            if hasattr(tr, "marker") and tr.marker is not None:
                tr.marker.opacity = 1.0
        return

    for tr in fig.data:
        cd = getattr(tr, "customdata", None)
        if cd is None:
            continue

        # customdata schema below:
        # [Label, Start_str, Finish_str, Type, UUID, Level, PhaseID, Status, PlannedDur_str, ActualDur_str, IsMilestone]
        uuids = [row[4] for row in cd]

        is_selected = [u == selected_uuid for u in uuids]
        any_selected_here = any(is_selected)

        # dim all bars in this trace if it contains no selected item
        if hasattr(tr, "marker") and tr.marker is not None:
            # opacity can be per-point or scalar; here we do per-point so mixed traces work
            tr.marker.opacity = [1.0 if s else 0.35 for s in is_selected]

            # per-point outline width/color for aesthetic highlight
            line_w = [3 if s else 1 for s in is_selected]
            line_c = ["rgba(0,0,0,0.85)" if s else "rgba(0,0,0,0.25)" for s in is_selected]

            tr.marker.line.width = line_w
            tr.marker.line.color = line_c

        # bring selected trace “forward” a bit
        if any_selected_here:
            tr.update(zorder=10)


@cache_data
def build_timeline(
    project: Project,
    inputs: GanttState,
    selected_uuid: str | None = None,
    delay_windows: tuple[tuple[str, str, dt.datetime, dt.datetime, int, str], ...] | None = None,
) -> go.Figure:
    df = build_gantt_df(project, inputs)
    if df is None or df.empty:
        raise ValueError(f"No data available to build Gantt timeline for project '{project.name}'.")

    allowed_types = []
    if inputs.show_planned:
        allowed_types.append("Planned")
    if inputs.show_actual:
        allowed_types.append("Actual")

    if not allowed_types:
        raise ValueError("Nothing to show: both planned and actual are turned off")


    df = df[df["Type"].isin(allowed_types)].copy()
    if df.empty:
        raise ValueError("No timeline rows match the current planned/actual filters.")
    
    color_map = build_color_map(
        df=df,
        planned_color=inputs.planned_color,
        actual_color=inputs.actual_color,
    )

    order = list(dict.fromkeys(df["RowID"].tolist()))
    label_map: dict[str, str] = {}
    for _, r in df.iterrows():
        rid = r["RowID"]
        if rid not in label_map:
            label_map[rid] = r["DisplayLabel"]

    is_milestone = (df["Level"] == "Task") & (df["Type"] == "Planned") & (df["IsMilestone"] == True)
    df_ms = df[is_milestone].copy()
    df_bar = df[~is_milestone].copy()

    x_range = [project.start_date, project.end_date]
    start_candidates = []
    end_candidates = []

    if inputs.show_planned:
        start_candidates.append(project.start_date)
        end_candidates.append(project.end_date)

    if inputs.show_actual:
        if project.actual_start:
            start_candidates.append(project.actual_start)

        if project.actual_end:
            end_candidates.append(project.actual_end)

    x_range = [
        min(start_candidates),
        max(end_candidates)
    ]

    if inputs.x_axis_start and inputs.x_axis_end:
        x_range = [inputs.x_axis_start, inputs.x_axis_end]

    fig = px.timeline(
        df_bar,
        x_start="Start",
        x_end="Finish",
        y="RowID",
        color="ColorKey",
        range_x=x_range,
        color_discrete_map=color_map,
        category_orders={"RowID": order},
        custom_data=[
            "Label",          #0
            "Start_str",      #1
            "Finish_str",     #2
            "Type",           #3
            "UUID",           #4
            "Level",          #5
            "PhaseID",        #6
            "Status",         #7
            "PlannedDur_str", #8
            "ActualDur_str",  #9
            "IsMilestone",    #10
        ],
    )

    ticktext = [label_map[v] for v in order]
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=order,
        tickmode="array",
        tickvals=order,
        ticktext=ticktext,
        autorange="reversed",
        title=None,
        automargin=True,
    )

    fig.update_xaxes(
        title="Project Time",
        automargin=True,
        showgrid=True,
        gridwidth=1,
    )

    for tr in fig.data:
        if isinstance(tr.name, str) and tr.name.count("|") >= 2:
            ph_name, level, typ = tr.name.split("|", 2)
            tr.legendgroup = ph_name
            tr.name = ph_name

            if level == "Phase":
                if inputs.show_planned:
                    tr.showlegend = (typ == "Planned")
                else:
                    tr.showlegend = (typ == "Actual")
            else:
                tr.showlegend = False

        if hasattr(tr, "marker") and tr.marker is not None:
            tr.marker.line.width = 1
            tr.marker.line.color = "rgba(0,0,0,0.25)"

    if not df_ms.empty:
        fig.add_trace(
            go.Scatter(
                x=df_ms["Start"],
                y=df_ms["RowID"],
                mode="markers",
                name="Milestone",
                marker=dict(symbol="diamond", size=10, line=dict(width=1.5, color="black")),
                customdata=np.stack(
                    [
                        df_ms["Label"],
                        df_ms["Start_str"],
                        df_ms["Finish_str"],
                        df_ms["Type"],
                        df_ms["UUID"],
                        df_ms["Level"],
                        df_ms["PhaseID"],
                        df_ms["Status"],
                        df_ms["PlannedDur_str"],
                        df_ms["ActualDur_str"],
                        df_ms["IsMilestone"],
                    ],
                    axis=1,
                ),
                hovertemplate = "<br>".join([
                    "<b>%{customdata[0]}</b>",
                    "<b>Start</b>: %{customdata[1]}",
                    "<b>Finish</b>: %{customdata[2]}",
                    "<b>Type</b>: %{customdata[3]}",
                    "<b>Planned</b>: %{customdata[8]}",
                    "<b>Actual</b>: %{customdata[9]}",
                    "<b>Status</b>: %{customdata[7]}",
                    "<span style='opacity:0.7'>Click to select</span>",
                ]) + "<extra></extra>",
                showlegend=True,
                legendgroup="milestones",
            )
        )

    for tr in fig.data:
        if getattr(tr, "customdata", None) is None:
            continue
        tr.hovertemplate = "<br>".join([
            "<b>%{customdata[0]}</b>",
            "<b>Start</b>: %{customdata[1]}",
            "<b>Finish</b>: %{customdata[2]}",
            "<b>Type</b>: %{customdata[3]}",
            "<b>Planned</b>: %{customdata[8]}",
            "<b>Actual</b>: %{customdata[9]}",
            "<b>Status</b>: %{customdata[7]}",
            "<span style='opacity:0.7'>Click to select</span>",
        ]) + "<extra></extra>"

    row_height = 28
    title_left = project.name.split("\n")[0]
    fig.update_layout(
        title=dict(
            text=f"<b>{title_left} Gantt</b>",
            y=1,
            x=0.5,
            xanchor="center",
            yanchor="top",
            font=dict(size=20),
        ),
        height=max(260, int(row_height * len(order))),
        margin=dict(l=10, r=10, t=20, b=10),
        legend_title_text="Phase",
        legend_tracegroupgap=6,
        showlegend=True,
        hovermode="closest",
        hoverlabel=dict(align="left", namelength=-1),
        legend=dict(groupclick="togglegroup", itemclick="toggleothers"),
        clickmode="event+select",
    )

    # Add delay overlays (bands + hover pins)
    if delay_windows:
        _add_delay_overlays(
            fig=fig,
            df=df,
            delay_windows=delay_windows,
            x_range=x_range,
            show_actual=inputs.show_actual,
        )

    _apply_selection_styling(fig, selected_uuid)
    return fig


# -----------------------------
# Optional: Click handling in Streamlit
# -----------------------------
def render_gantt_with_click_selection(fig: go.Figure, key: str = "gantt"):
    """
    Renders the gantt and captures click events if streamlit_plotly_events is available.
    On click, writes:
      - gantt_selected_uuid
      - gantt_selected_phase_id
      - gantt_selected_payload
    into st.session_state.
    """
    try:
        from streamlit_plotly_events import plotly_events
        events = plotly_events(fig, click_event=True, hover_event=False, select_event=False, key=key)
    except Exception:
        # Fallback: render without click capture
        st.plotly_chart(fig, key=f"{key}_static")
        events = []

    if events:
        # Plotly event points usually include "customdata" from the clicked point
        pt = events[0]
        cd = pt.get("customdata", None)
        if cd:
            # cd schema:
            # [Label, Start_str, Finish_str, Type, UUID, Level, PhaseID, Status, PlannedDur_str, ActualDur_str, IsMilestone]
            uuid = cd[4]
            level = cd[5]
            phase_id = cd[6]

            if uuid and level == "Task":
                st.session_state["gantt_selected_uuid"] = uuid
                st.session_state["gantt_selected_phase_id"] = phase_id
                st.session_state["gantt_selected_payload"] = {
                    "uuid": uuid,
                    "phase_id": phase_id,
                    "name": cd[0],
                    "planned_start_str": cd[1],
                    "planned_finish_str": cd[2],
                    "type": cd[3],
                    "status": cd[7],
                    "planned_duration_str": cd[8],
                    "actual_duration_str": cd[9],
                    "is_milestone": bool(cd[10]),
                }
            else:
                # clicked a phase row or something else
                st.session_state["gantt_selected_uuid"] = None
                st.session_state["gantt_selected_phase_id"] = phase_id
                st.session_state["gantt_selected_payload"] = None
 