import pandas as pd
import plotly.express as px
import streamlit as st
from typing import Optional
from plotly.colors import qualitative as q
import plotly.graph_objects as go
import numpy as np
import re
from colorsys import rgb_to_hls, hls_to_rgb

_rgb_re = re.compile(r"^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*([\d.]+))?\s*\)$", re.IGNORECASE)

def _parse_color_any(c: str):
    c = c.strip()
    if c.startswith("#"):
        h = c[1:]
        if len(h) == 3:
            r, g, b = (int(h[i]*2, 16) for i in range(3))
        elif len(h) == 6:
            r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        else:
            raise ValueError(f"Unsupported hex color length: {c}")
        return (r/255.0, g/255.0, b/255.0)
    m = _rgb_re.match(c)
    if m:
        r, g, b = (int(m.group(i)) for i in (1,2,3))
        return (r/255.0, g/255.0, b/255.0)
    raise ValueError(f"Color format not supported for adjustment: {c}")

def _to_hex(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(max(0,min(1,r))*255),
                                        int(max(0,min(1,g))*255),
                                        int(max(0,min(1,b))*255))

def adjust_color_any(color: str, *, lighten: float = 0.0, darken: float = 0.0) -> str:
    if lighten and darken:
        raise ValueError("Use either lighten or darken, not both.")
    r, g, b = _parse_color_any(color)
    h, l, s = rgb_to_hls(r, g, b)
    if lighten > 0:
        l = l + (1 - l) * lighten
    elif darken > 0:
        l = l * (1 - darken)
    r2, g2, b2 = hls_to_rgb(h, l, s)
    return _to_hex(r2, g2, b2)

def render_gantt(session):
    phases = session.project.phases
    if not phases:
        st.info("Add a phase and some tasks to your project to view the visualizer.")
        return

    st.subheader("Project Plan")

    expander = st.expander("Gantt Chart")
    # Controls
    col_left, _ = expander.columns([1, 3])
    with col_left:
        with st.container(border=True):
            show_actual = st.toggle(
                "Show actual durations",
                value=False,
                disabled=not getattr(session.project, "has_actuals", False),
                key="gantt_show_actual",
            )
            use_bta_colors = st.toggle(  # label text can be changed later if you want
                "Use BTA color scheme",
                value=True,
                key="gantt_use_bta_colors",
            )
            shade_non_working = st.toggle(
                "Shade non-working time",
                value=True,
                key="gantt_shade_non_working",
                help="Go to settings to edit working days/hours for the project"
            )

    # Build rows (planned + optional actual), with unique RowIDs
    rows: list[dict] = []

    # Prefer explicit phase_order if present, otherwise use dict order
    phase_ids = getattr(session.project, "phase_order", list(phases.keys()))
    for ph_id in phase_ids:
        ph = phases[ph_id]

        # Planned phase
        rows.append({
            "RowID": f"PH:{ph_id}",
            "Label": f"{ph.name}",
            "Phase": ph.name,
            "Start": getattr(ph, "start_date", None),
            "Finish": getattr(ph, "end_date", None),
            "Level": "Phase",
            "Type": "Planned",
            "UUID": None,
            "Predecessors": [],
        })

        # Actual phase (only if both exist)
        astart = getattr(ph, "actual_start", None)
        aend = getattr(ph, "actual_end", None)
        if show_actual and astart is not None and aend is not None:
            rows.append({
                "RowID": f"PH:{ph_id}",
                "Label": f"{ph.name}",
                "Phase": ph.name,
                "Start": astart,
                "Finish": aend,
                "Level": "Phase",
                "Type": "Actual",
                "UUID": None,
                "Predecessors": [],
            })

        # Tasks
        task_ids = getattr(ph, "task_order", list(getattr(ph, "tasks", {}).keys()))
        for t_id in task_ids:
            t = ph.tasks[t_id]

            uuid = getattr(t, "uuid", None)
            preds = getattr(t, "predecessor_ids", None)
            preds = list(preds) if preds is not None else []

            # Planned task
            rows.append({
                "RowID": f"TK:{t_id}",
                "Label": t.name,
                "Phase": ph.name,
                "Start": getattr(t, "start_date", None),
                "Finish": getattr(t, "end_date", None),
                "Level": "Task",
                "Type": "Planned",
                "UUID": uuid,
                "Predecessors": preds,
            })

            # Actual task (only if both exist)
            astart_t = getattr(t, "actual_start", None)
            aend_t = getattr(t, "actual_end", None)
            if show_actual and astart_t is not None and aend_t is not None:
                rows.append({
                    "RowID": f"TK:{t_id}",
                    "Label": t.name,
                    "Phase": ph.name,
                    "Start": astart_t,
                    "Finish": aend_t,
                    "Level": "Task",
                    "Type": "Actual",
                    "UUID": uuid,
                    "Predecessors": preds,
                })

    df = pd.DataFrame(rows)
    if df.empty:
        expander.info("No tasks or phases with dates to display.")
        return

    # Filter out rows without valid start/finish
    df = df[df["Start"].notna() & df["Finish"].notna()].copy()
    if df.empty:
        expander.info("No tasks or phases with both start and finish dates.")
        return

    # Establish ordering and labels (preserve insertion order)
    order = list(dict.fromkeys(df["RowID"].tolist()))
    label_map: dict[str, str] = {}
    for _, r in df.iterrows():
        rid = r["RowID"]
        if rid not in label_map:
            label_map[rid] = r["Label"]

    # ----- Colors -----
    # New scheme:
    # - Each phase gets a base color.
    # - Planned Phase = slightly darkened base
    # - Planned Task  = slightly lightened base
    # - Actual Phase  = more darkened base
    # - Actual Task   = more lightened base
    df["ColorKey"] = df.apply(
        lambda r: f"{r['Phase']}|{r['Level']}|{r['Type']}", axis=1
    )

    if use_bta_colors:
        # Custom, muted palette for phases
        phase_palette = [
            "#264653",  # deep blue-green
            "#2A9D8F",  # teal
            "#8E5572",  # mauve
            "#4361EE",  # blue
            "#F4A261",  # soft orange
            "#6D597A",  # purple
            "#2F4858",  # slate
        ]

        phase_names = df["Phase"].dropna().unique().tolist()
        color_map: dict[str, str] = {}
        for i, ph_name in enumerate(phase_names):
            base = phase_palette[i % len(phase_palette)]
            # planned
            color_map[f"{ph_name}|Phase|Planned"] = adjust_color_any(base, darken=0.20)
            color_map[f"{ph_name}|Task|Planned"] = adjust_color_any(base, lighten=0.25)
            # actual (more contrast)
            color_map[f"{ph_name}|Phase|Actual"] = adjust_color_any(base, darken=0.45)
            color_map[f"{ph_name}|Task|Actual"] = adjust_color_any(base, lighten=0.55)

        legend_title = "Phase"
        color_column = "ColorKey"
    else:
        # Fallback: still per-phase, but use built-in Plotly palettes
        palette = q.Plotly + q.Set3 + q.Pastel + q.Safe + q.Dark24

        def base_color(key: str) -> str:
            return palette[hash(key) % len(palette)]

        color_map: dict[str, str] = {}
        for ph_name in df["Phase"].dropna().unique().tolist():
            base = base_color(ph_name)
            color_map[f"{ph_name}|Phase|Planned"] = adjust_color_any(base, darken=0.20)
            color_map[f"{ph_name}|Task|Planned"] = adjust_color_any(base, lighten=0.25)
            color_map[f"{ph_name}|Phase|Actual"] = adjust_color_any(base, darken=0.45)
            color_map[f"{ph_name}|Task|Actual"] = adjust_color_any(base, lighten=0.55)

        legend_title = "Phase"
        color_column = "ColorKey"

    df["Start_str"] = pd.to_datetime(df["Start"]).dt.strftime("%Y-%m-%d %H:%M")
    df["Finish_str"] = pd.to_datetime(df["Finish"]).dt.strftime("%Y-%m-%d %H:%M")

    # ----- Base timeline -----
    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="RowID",
        color=color_column,
        color_discrete_map=color_map,
        category_orders={"RowID": order},
        custom_data=["Label", "Start_str", "Finish_str", "Type"],
    )

    

    # Y-axis: force order so first phase/task is at the top
    fig.update_yaxes(
        categoryorder="array",
        categoryarray=order,
        tickmode="array",
        tickvals=order,
        ticktext=[label_map[v] for v in order],
        autorange="reversed",
        title=None,
    )
    fig.update_xaxes(title=None)

    # Legend grouping by phase so clicking a phase toggles its tasks as well
    for tr in fig.data:
        if isinstance(tr.name, str) and tr.name.count("|") >= 2:
            ph_name, level, typ = tr.name.split("|", 2)
            tr.legendgroup = ph_name
            tr.name = ph_name
            tr.showlegend = (level == "Phase" and typ == "Planned")
        tr.marker.line.width = 1
        tr.marker.line.color = "rgba(0,0,0,0.25)"

    # ----- Shade non-working days (weekends) -----
    if shade_non_working and hasattr(session.project, "settings"):
        working_days = getattr(session.project.settings, "working_days", None)

        if not session.project.settings.work_all_day:
            work_start_time = getattr(session.project.settings, "work_start_time", None)
            work_end_time = getattr(session.project.settings, "work_end_time", None)

        if working_days and not session.project.settings.work_all_day:
            start_min = df["Start"].min()
            finish_max = df["Finish"].max()
            if pd.notna(start_min) and pd.notna(finish_max):
                start_date = start_min.floor("D")
                end_date = finish_max.ceil("D")
                cur = start_date
                while cur <= end_date:
                    wd = cur.weekday()  # 0 = Monday
                    if 0 <= wd < len(working_days) and not working_days[wd]:
                        x0 = cur
                        x1 = cur + pd.Timedelta(days=1)
                        fig.add_vrect(
                            x0=x0,
                            x1=x1,
                            fillcolor="lightgrey",
                            opacity=0.12,
                            layer="below",
                            line_width=0,
                            yref="paper",  # full vertical span, but won't affect scaling
                            y0=0,
                            y1=1,
                        )
                    cur += pd.Timedelta(days=1)

    # ----- Dependency arrows between tasks (planned only) -----
    task_planned = df[
        (df["Level"] == "Task")
        & (df["Type"] == "Planned")
        & df["Start"].notna()
        & df["Finish"].notna()
    ].copy()

    uuid_to_row: dict[str, pd.Series] = {}
    for _, row in task_planned.iterrows():
        uid = row.get("UUID")
        if pd.notna(uid):
            uuid_to_row[uid] = row

    for _, rowB in task_planned.iterrows():
        preds = rowB.get("Predecessors", [])
        if preds is None:
            continue
        if not isinstance(preds, (list, tuple, np.ndarray)):
            continue
        for pred_uuid in preds:
            rowA = uuid_to_row.get(pred_uuid)
            if rowA is None:
                continue
            fig.add_annotation(
                x=rowB["Start"],
                y=rowB["RowID"],
                ax=rowA["Finish"],
                ay=rowA["RowID"],
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=3,
                arrowsize=1,
                arrowwidth=1,
                arrowcolor="rgba(80,80,80,0.7)",
                opacity=0.8,
            )

    # ----- Phase end markers (planned + actual), with high-contrast colors -----
    phase_planned = df[
        (df["Level"] == "Phase")
        & (df["Type"] == "Planned")
        & df["Finish"].notna()
    ]
    if not phase_planned.empty:
        fig.add_trace(
            go.Scatter(
                x=phase_planned["Finish"],
                y=phase_planned["RowID"],
                mode="markers",
                name="Phase End (Planned)",
                marker=dict(
                    symbol="diamond",
                    size=11,
                    color="#FFB703",  # bright amber
                    line=dict(width=1.5, color="black"),
                ),
                hoverinfo="skip",
                showlegend=True,
                legendgroup="PhaseEndPlanned",
            )
        )

    phase_actual = df[
        (df["Level"] == "Phase")
        & (df["Type"] == "Actual")
        & df["Finish"].notna()
    ]
    if show_actual and not phase_actual.empty:
        fig.add_trace(
            go.Scatter(
                x=phase_actual["Finish"],
                y=phase_actual["RowID"],
                mode="markers",
                name="Phase End (Actual)",
                marker=dict(
                    symbol="circle",
                    size=10,
                    color="#E63946",  # strong red/pink
                    line=dict(width=1.5, color="black"),
                ),
                hoverinfo="skip",
                showlegend=True,
                legendgroup="PhaseEndActual",
            )
        )

    # ----- Layout / hover -----
    # Slightly smaller row height + smaller top margin to reduce whitespace
    row_height = 28
    fig.update_layout(
        height=max(220, int(row_height * len(order))),
        margin=dict(l=10, r=10, t=20, b=10),
        legend_title_text=legend_title,
        legend_tracegroupgap=6,
        showlegend=True,
        hoverlabel=dict(namelength=-1),
        legend=dict(groupclick="togglegroup", itemclick="toggleothers"),
    )

    # Only set hovertemplate on traces that actually have customdata
    for tr in fig.data:
        if getattr(tr, "customdata", None) is not None:
            tr.hovertemplate = (
                "<b>%{customdata[0]}</b><br>"
                "Start: %{customdata[1]}<br>"
                "Finish: %{customdata[2]}<br>"
                "Type: %{customdata[3]}<extra></extra>"
            )

    expander.plotly_chart(fig, use_container_width=True)


def render_task_details(session):
    st.subheader("Task Details")
    c1, _, c3, c4 = st.columns([1,7,1,1])

    phase_to_use = c1.selectbox(
        label="Filter by Phase",
        options= ["All Phases"] + [pid for pid in session.project.phase_order],
        format_func=lambda pid: "All Phases" if pid == "All Phases" else session.project.phases[pid].name,
        help="Filter the task details table to show only tasks from a specific phase"
    )

    only_show_delayed = c3.toggle(
        label="Show only delayed tasks",
        value = True,
        key="show_delayed_tasks"
    )

    show_durations = c4.toggle(
        label="Show task durations",
        value=False,
        key="show_task_durations"
    )

    task_df = session.project.get_task_df()
    if phase_to_use != "All Phases":
        task_df = task_df[task_df["pid"] == phase_to_use]
        task_df.drop(columns=["pid"], axis=1, inplace=True)

    task_df = task_df[task_df["actual_duration"].notna()]
    task_df["delay"] = task_df["actual_duration"] - task_df["planned_duration"]

    if only_show_delayed:
        task_df = task_df[task_df["delay"] > 0]

    if not show_durations:
        task_df.drop(columns=["planned_start","planned_end","actual_start", "actual_end"], axis=1, inplace=True)
    
    st.dataframe(
        task_df,
        column_config={
            "task": st.column_config.TextColumn("Task Name"),
            "planned_start": st.column_config.DatetimeColumn("Planned Start"),
            "planned_end": st.column_config.DatetimeColumn("Planned End"),
            "actual_start": st.column_config.DatetimeColumn("Actual Start"),
            "actual_end": st.column_config.DatetimeColumn("Actual End"),
            "planned_duration": st.column_config.NumberColumn("Planned Duration (hrs)", format="%.2f"),
            "actual_duration": st.column_config.NumberColumn("Actual Duration (hrs)", format="%.2f"),
            "delay": st.column_config.NumberColumn("Delay (hrs)", format="%.2f", help="Positive values indicate the task finished later than planned; negative values indicate it finished earlier."),
            "notes": st.column_config.TextColumn("Notes")
        },
        width='stretch',
        hide_index=True
    )

