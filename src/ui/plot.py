import pandas as pd
import plotly.express as px
import streamlit as st
from typing import Optional
from plotly.colors import qualitative as q
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

    # Controls
    col_left, col_right = st.columns(2)
    with col_left:
        show_actual = st.checkbox("Show actual durations", value=True)
    with col_right:
        use_bta_colors = st.checkbox("Use BTA color scheme", value=False)

    # Build rows (planned + optional actual), with unique RowIDs
    rows = []
    for ph_id in session.project.phase_order:
        ph = session.project.phases[ph_id]
        # Planned phase
        rows.append({
            "RowID": f"PH:{ph_id}",
            "Label": f"{ph.name}",
            "Phase": ph.name,
            "Start": ph.start_date,
            "Finish": ph.end_date,
            "Level": "Phase",
            "Type": "Planned",
        })
        # Actual phase (only if both exist)
        if show_actual:
            astart = getattr(ph, "actual_start", None)
            aend   = getattr(ph, "actual_end", None)
            if astart is not None and aend is not None:
                rows.append({
                    "RowID": f"PH:{ph_id}",
                    "Label": f"{ph.name}",
                    "Phase": ph.name,
                    "Start": astart,
                    "Finish": aend,
                    "Level": "Phase",
                    "Type": "Actual",
                })

        # Tasks
        for t_id in ph.task_order:
            t = ph.tasks[t_id]
            label = f"{ph.name}: {t.name}"
            # Planned task
            rows.append({
                "RowID": f"TK:{t_id}",
                "Label": label,
                "Phase": ph.name,
                "Start": t.start_date,
                "Finish": t.end_date,
                "Level": "Task",
                "Type": "Planned",
            })
            # Actual task (only if both exist)
            if show_actual and getattr(t, "actual_start", None) is not None and getattr(t, "actual_end", None) is not None:
                rows.append({
                    "RowID": f"TK:{t_id}",
                    "Label": label,
                    "Phase": ph.name,
                    "Start": t.actual_start,
                    "Finish": t.actual_end,
                    "Level": "Task",
                    "Type": "Actual",
                })

    if not rows:
        st.info("Add a task to your project to view the visualizer.")
        return

    df = pd.DataFrame(rows)

    # Normalize times & helpers
    df["Start"]  = pd.to_datetime(df["Start"],  errors="coerce").dt.tz_localize(None)
    df["Finish"] = pd.to_datetime(df["Finish"], errors="coerce").dt.tz_localize(None)
    df["_FinishStr"] = df["Finish"].dt.strftime("%Y-%m-%d %H:%M").fillna("")
    df["_Title"] = df.apply(
        lambda r: r["Phase"] if r["Level"] == "Phase" else r["Label"],
        axis=1
    )

    # Ordered categories for the y-axis using RowID (unique)
    order = list(dict.fromkeys([r["RowID"] for r in rows]))
    df["RowID"] = pd.Categorical(df["RowID"], categories=order, ordered=True)
    label_map = {r["RowID"]: r["Label"] for r in rows}
    tickvals = order
    ticktext = [label_map[v] for v in tickvals]

    # Coloring
    if use_bta_colors:
        # Keep per-phase ColorKey so we can have a per-phase legend group.
        df["ColorKey"] = df.apply(lambda r: f"{r['Phase']}|{r['Level']}|{r['Type']}", axis=1)

        # Map EVERY phase+level+type to the fixed BTA colors
        color_map = {}
        unique_phases = df["Phase"].dropna().unique().tolist()
        for ph_name in unique_phases:
            color_map[f"{ph_name}|Phase|Planned"] = "#2A9E77"  # dark green
            color_map[f"{ph_name}|Task|Planned"]  = "#61D5AE"  # light green
            color_map[f"{ph_name}|Phase|Actual"]  = "#F4B084"  # orange
            color_map[f"{ph_name}|Task|Actual"]   = "#F8CBAD"  # peach
        legend_title = "Phase"

        # No hatching in BTA mode
        timeline_kwargs = dict(
            data_frame=df,
            x_start="Start",
            x_end="Finish",
            y="RowID",
            color="ColorKey",
            color_discrete_map=color_map,
            custom_data=["_Title", "Start", "_FinishStr", "Type"],
            hover_data={"ColorKey": False},
        )
    else:
        # Original per-phase palette + patterns (Phase has hatch)
        pattern_map = {"Phase": "\\", "Task": ""}
        palette = q.Plotly + q.Set3 + q.Pastel + q.Safe + q.Dark24
        def base_color(key: str) -> str:
            return palette[hash(key) % len(palette)]

        df["ColorKey"] = df.apply(lambda r: f"{r['Phase']}|{r['Level']}|{r['Type']}", axis=1)
        color_map = {}
        for ph_name in df["Phase"].unique().tolist():
            base = base_color(ph_name)
            color_map[f"{ph_name}|Phase|Planned"] = adjust_color_any(base, darken=0.35)
            color_map[f"{ph_name}|Task|Planned"]  = adjust_color_any(base, lighten=0.35)
            color_map[f"{ph_name}|Phase|Actual"]  = adjust_color_any(base, darken=0.60)
            color_map[f"{ph_name}|Task|Actual"]   = adjust_color_any(base, lighten=0.60)
        legend_title = "Phase"

        timeline_kwargs = dict(
            data_frame=df,
            x_start="Start",
            x_end="Finish",
            y="RowID",
            color="ColorKey",
            color_discrete_map=color_map,
            pattern_shape="Level",
            pattern_shape_map=pattern_map,
            custom_data=["_Title", "Start", "_FinishStr", "Type"],
            hover_data={"ColorKey": False},
        )

    fig = px.timeline(**timeline_kwargs)

    # Y-axis labels
    fig.update_yaxes(
        autorange="reversed",
        categoryorder="array",
        categoryarray=tickvals,
        tickmode="array",
        tickvals=tickvals,
        ticktext=ticktext,
    )

    # Phase-isolation legend: one legend item per phase (the Planned-Phase trace),
    # and group all traces of that phase together so clicking toggles the whole phase.
    for tr in fig.data:
        if isinstance(tr.name, str) and tr.name.count("|") >= 2:
            ph_name, level, typ = tr.name.split("|", 2)
            tr.legendgroup = ph_name
            tr.name = ph_name
            tr.showlegend = (level == "Phase" and typ == "Planned")
        tr.marker.line.width = 1
        tr.marker.line.color = "rgba(0,0,0,0.25)"

    row_height = 36
    fig.update_layout(
        height=max(240, row_height * len(tickvals)),
        margin=dict(l=10, r=10, t=40, b=10),
        legend_title_text=legend_title,
        legend_tracegroupgap=6,
        showlegend=True,
        hoverlabel=dict(namelength=-1),
        # Make legend interactions phase-friendly:
        legend=dict(groupclick="togglegroup", itemclick="toggleothers"),
    )

    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>"
                      "Start: %{customdata[1]|%Y-%m-%d %H:%M}<br>"
                      "Finish: %{customdata[2]}<br>"
                      "Type: %{customdata[3]}<extra></extra>"
    )

    st.plotly_chart(fig, use_container_width=True)
