import pandas as pd
import plotly.express as px
import streamlit as st
from typing import List
from colorsys import rgb_to_hls, hls_to_rgb
from plotly.colors import qualitative as q
import re
from colorsys import rgb_to_hls, hls_to_rgb

_rgb_re = re.compile(r"^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*([\d.]+))?\s*\)$", re.IGNORECASE)

def _parse_color_any(c: str):
    """
    Accepts '#RGB', '#RRGGBB', 'rgb(r,g,b)', 'rgba(r,g,b,a)'.
    Returns floats (r,g,b) in [0,1].
    """
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

    # Last resort: let Plotly accept the original string without adjustment
    # by raising a clear error if we try to adjust it.
    raise ValueError(f"Color format not supported for adjustment: {c}")

def _to_hex(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(max(0,min(1,r))*255),
                                        int(max(0,min(1,g))*255),
                                        int(max(0,min(1,b))*255))

def adjust_color_any(color: str, *, lighten: float = 0.0, darken: float = 0.0) -> str:
    """
    Lighten/darken a color given as hex or rgb/rgba string.
    Returns hex '#RRGGBB' (stable for Plotly).
    """
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

    rows = []
    for ph in phases.values():
        rows.append({
            "Phase": ph.name,
            "Task": f"◼ {ph.name}",
            "Start": ph.start_date,
            "Finish": ph.end_date,
            "Kind": "Phase",
        })
        for t in ph.tasks.values():
            rows.append({
                "Phase": ph.name,
                "Task": t.name,
                "Start": t.start_date,
                "Finish": t.end_date,
                "Kind": "Task",
            })

    if not rows:
        st.info("Add a task to your project to view the visualizer.")
        return

    df = pd.DataFrame(rows)
    df["Task"] = pd.Categorical(df["Task"], categories=[r["Task"] for r in rows], ordered=True)

    palette = q.Plotly + q.Set3 + q.Pastel + q.Safe + q.Dark24
    def base_color(key: str) -> str:
        return palette[hash(key) % len(palette)]

    df["ColorKey"] = df.apply(lambda r: f"{r['Phase']}|{r['Kind']}", axis=1)

    color_map = {}
    for ph_name in df["Phase"].unique().tolist():
        base = base_color(ph_name)  # may be '#...' or 'rgb(...)'
        color_map[f"{ph_name}|Phase"] = adjust_color_any(base, darken=0.35)
        color_map[f"{ph_name}|Task"]  = adjust_color_any(base, lighten=0.35)

    pattern_map = {"Phase": "\\", "Task": ""}

    fig = px.timeline(
        df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="ColorKey",
        color_discrete_map=color_map,
        pattern_shape="Kind",
        pattern_shape_map=pattern_map,
        # make these available to hovertemplate:
        custom_data=df[["Phase", "Kind", "Start", "Finish"]],
        hover_data={"ColorKey": False},  # keep extra clean
    )

    fig.update_yaxes(autorange="reversed")

    for tr in fig.data:
        if isinstance(tr.name, str) and "|" in tr.name:
            ph_name, kind = tr.name.split("|", 1)
            tr.legendgroup = ph_name
            tr.name = ph_name
            tr.showlegend = (kind == "Phase")
        tr.marker.line.width = 1
        tr.marker.line.color = "rgba(0,0,0,0.25)"

    row_height = 36
    fig.update_layout(
        height=max(240, row_height * df["Task"].nunique()),
        margin=dict(l=10, r=10, t=40, b=10),
        legend_title_text="Phase",
        hoverlabel=dict(namelength=-1),
    )

    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b> — %{y}<br>"
                      "Type: %{customdata[1]}<br>"
                      "Start: %{customdata[2]|%Y-%m-%d %H:%M}<br>"
                      "Finish: %{customdata[3]|%Y-%m-%d %H:%M}<extra></extra>"
    )

    st.plotly_chart(fig, use_container_width=True)
