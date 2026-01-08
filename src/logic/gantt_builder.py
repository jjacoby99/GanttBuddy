import pandas as pd
from plotly.colors import qualitative as q
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from models.project import Project
from models.phase import Phase
from models.task import Task
from models.session import SessionModel
from models.gantt_models import GanttInputs

from logic.plot_utilities import adjust_color_any

def build_gantt_df(project: Project, inputs: GanttInputs) -> pd.DataFrame:
    
    phases = project.phases
    rows: list[dict] = []

    # Prefer explicit phase_order if present, otherwise use dict order
    phase_ids = getattr(project, "phase_order", list(phases.keys()))
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
        if inputs.show_actuals and astart is not None and aend is not None:
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
            if inputs.show_actuals and astart_t is not None and aend_t is not None:
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
        return None
    # Filter out rows without valid start/finish
    df = df[df["Start"].notna() & df["Finish"].notna()].copy()
    if df.empty:
        return None

    

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

    

    df["Start_str"] = pd.to_datetime(df["Start"]).dt.strftime("%Y-%m-%d %H:%M")
    df["Finish_str"] = pd.to_datetime(df["Finish"]).dt.strftime("%Y-%m-%d %H:%M")

    return df


def build_color_map(df: pd.DataFrame, use_bta_colors: bool) -> dict[str, str]:
    if df is None or df.empty:
        return {}

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
        return color_map
    
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
    return color_map


def build_timeline(project: Project, inputs: GanttInputs):
    
    df = build_gantt_df(project, inputs)

    if df is None or df.empty:
        raise ValueError(f"No data available to build Gantt timeline for project '{project.name}'.")
    
    color_map = build_color_map(
        df=df,
        use_bta_colors=inputs.use_bta_colors
    )

    order = list(dict.fromkeys(df["RowID"].tolist()))

    # Establish ordering and labels (preserve insertion order)
    label_map: dict[str, str] = {}
    for _, r in df.iterrows():
        rid = r["RowID"]
        if rid not in label_map:
            label_map[rid] = r["Label"]
    
    # ----- Base timeline -----
    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="RowID",
        color="ColorKey",
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
    if inputs.shade_non_working:
        working_days = getattr(project.settings, "working_days", None)

        if not project.settings.work_all_day:
            work_start_time = getattr(project.settings, "work_start_time", None)
            work_end_time = getattr(project.settings, "work_end_time", None)

        if working_days and not project.settings.work_all_day:
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
    if inputs.show_actuals and not phase_actual.empty:
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
    legend_title = "Phase"
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
    return fig