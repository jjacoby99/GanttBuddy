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

# -----------------------------
# Build DF with the extra info you need
# -----------------------------
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
def build_timeline(project: Project, inputs: GanttState, selected_uuid: str | None = None) -> go.Figure:
    df = build_gantt_df(project, inputs)
    if df is None or df.empty:
        raise ValueError(f"No data available to build Gantt timeline for project '{project.name}'.")

    color_map = build_color_map(
        df=df,
        planned_color=inputs.planned_color,
        actual_color=inputs.actual_color,
    )

    # preserve your insertion order for y
    order = list(dict.fromkeys(df["RowID"].tolist()))
    labels = list(dict.fromkeys(df["DisplayLabel"].tolist()))
    label_map = {}
    for _, r in df.iterrows():
        rid = r["RowID"]
        if rid not in label_map:
            label_map[rid] = r["DisplayLabel"]

    # Split milestones out (bars with zero duration are basically invisible)
    is_milestone = (df["Level"] == "Task") & (df["Type"] == "Planned") & (df["IsMilestone"] == True)
    df_ms = df[is_milestone].copy()
    df_bar = df[~is_milestone].copy()

    x_range = [min(project.start_date, project.actual_start if project.actual_start else project.start_date), 
               max(project.end_date, project.actual_end if project.actual_end else project.end_date)]
    if inputs.x_axis_start and inputs.x_axis_end:
        x_range = [inputs.x_axis_start, inputs.x_axis_end]

    # Base timeline bars
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
            "Label",                #0
            "Start_str",            #1
            "Finish_str",           #2
            "Type",                 #3
            "UUID",                 #4
            "Level",                #5
            "PhaseID",              #6
            "Status",               #7
            "PlannedDur_str",       #8
            "ActualDur_str",        #9
            "IsMilestone",          #10
        ],
    )

    ticktext = [label_map[v] for v in order]
    # Y-axis formatting: show phases + indented tasks
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=order,
        tickmode="array",
        tickvals=order,
        ticktext=ticktext,
        autorange="reversed",
        title=None,
        automargin=True
    )

    # fig.update_layout(
    #     margin=dict(l=compute_left_margin(ticktext),right=10,t=20,b=10)
    # )
    fig.update_xaxes(
        title="Project Time",
        automargin=True,
        showgrid=True,
        gridwidth=1,
    )

    # Legend grouping by phase (your approach, but keep the trace name readable)
    for tr in fig.data:
        if isinstance(tr.name, str) and tr.name.count("|") >= 2:
            ph_name, level, typ = tr.name.split("|", 2)
            tr.legendgroup = ph_name
            tr.name = ph_name
            tr.showlegend = (level == "Phase" and typ == "Planned")

        # base outline (selection styling will override per-point)
        if hasattr(tr, "marker") and tr.marker is not None:
            tr.marker.line.width = 1
            tr.marker.line.color = "rgba(0,0,0,0.25)"

    # Milestone diamonds (planned tasks only)
    if not df_ms.empty:
        fig.add_trace(
            go.Scatter(
                x=df_ms["Start"],
                y=df_ms["RowID"],
                mode="markers",
                name="Milestone",
                marker=dict(symbol="diamond", size=10, line=dict(width=1.5, color="black")),
                # mirror the same customdata layout so clicks/hover are consistent
                customdata=np.stack([
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
                ], axis=1),
                hovertemplate=(
                    "<b>%{customdata[0]}\n</b><br>"
                    "Start: %{customdata[1]}<br>"
                    "Type: %{customdata[3]}<br>"
                    "Planned: %{customdata[8]}<br>"
                    "Status: %{customdata[7]}<br>"
                    "<span style='opacity:0.7'>\"Click to select\"</span>"
                    "<extra></extra>"
                ),
                showlegend=True,
                legendgroup="milestones",
            )
        )

    # Hover template for bar traces
    for tr in fig.data:
        if getattr(tr, "customdata", None) is None:
            
            continue
        tr.hovertemplate = (
            "<b>%{customdata[0]}</b><br>"
            "<b>Start</b>: %{customdata[1]}<br>"
            "<b>Finish</b>: %{customdata[2]}<br>"
            "<b>Type</b>: %{customdata[3]}<br>"
            "<b>Planned</b>: %{customdata[8]}<br>"
            # Actual only if exists (string will be "" otherwise)
            "<b>Actual</b>: %{customdata[9]}<br>"
            "<b>Status</b>: %{customdata[7]}<br>"
            "<span style='opacity:0.7'>Click to select</span>"
            "<extra></extra>"
        )

    # Layout polish
    row_height = 28
    fig.update_layout(
        title={
            'text': f"<b>{project.name.split("\n")[0]} Gantt<b>",
            'y': 1,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=20)
        },
        height=max(260, int(row_height * len(order))),
        margin=dict(l=10, r=10, t=20, b=10),
        legend_title_text="Phase",
        legend_tracegroupgap=6,
        showlegend=True,
        hovermode="closest",
        hoverlabel=dict(
            align="left",
            namelength=-1
        ),
        legend=dict(groupclick="togglegroup", itemclick="toggleothers"),
        clickmode="event+select",
    )

    # Apply selection styling after the figure is built
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
 