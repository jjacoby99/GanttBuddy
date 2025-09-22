import streamlit as st
import plotly.express as px
from plotly.colors import qualitative as q
import pandas as pd

def render_gantt(session):
    phases = session.project.phases
    if not phases:
        st.info(f"Add a phase and some tasks to your project to view the visualizer.")
        return
    
    rows = []
    for ph in phases:
        for t in ph.tasks:
            rows.append({
                "Phase": ph.name,
                "Task": t.name,
                "Start": t.start_date,
                "Finish": t.end_date,
            })

    df = pd.DataFrame(rows)

    df["Task"] = pd.Categorical(df["Task"], categories=[r["Task"] for r in rows], ordered=True)

    # Deterministic phase -> color map
    #    (hash id/name -> pick from a big qualitative palette)
    palette = q.Plotly + q.Set3 + q.Pastel + q.Safe + q.Dark24  
    phase_names = df["Phase"].unique().tolist()
    def pick_color(key: str) -> str:
        return palette[hash(key) % len(palette)]

    color_map = {ph: pick_color(ph) for ph in phase_names}

    fig = px.timeline(
        df, x_start="Start", x_end="Finish", y="Task", color="Phase",
        color_discrete_map=color_map
    )
    fig.update_yaxes(autorange="reversed")

    # Row height control
    row_height = 40
    fig.update_layout(height=max(200, row_height * df["Task"].nunique()))

    st.plotly_chart(fig, use_container_width=True)
