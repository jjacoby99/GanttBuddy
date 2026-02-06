import streamlit as st
from models.project import Project
from typing import Literal

def render_project_info(project: Project, resolution: Literal["Phase", "Task"] = "Task"):
    with st.container():
        c1, c2 = st.columns(2)
        if resolution == "Task":
            n_tasks = len(project) - len(project.phase_order)
            label = "Number of Tasks"
        else:
            n_tasks = len(project.phase_order)
            label = "Number of Phases"
        
        c1.metric(
            label=label,
            value=n_tasks
        )
            
        total_minutes = int(project.planned_duration.total_seconds() // 60)
        h, m = divmod(total_minutes, 60)
        s = f"{h}h {m}m"
        c2.metric(
            label="Planned Duration",
            value=s
        )

        c1.metric(
            label="Planned Start",
            value=project.start_date.strftime("%b %d, %Y %I:%M").replace(" 0", " ")
        )

        c2.metric(
            label="Planned End",
            value=project.end_date.strftime("%b %d, %Y %I:%M").replace(" 0", " ")
        )
        
       