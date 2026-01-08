import pandas as pd
from plotly.colors import qualitative as q

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

    if inputs.use_bta_colors:
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

    return df