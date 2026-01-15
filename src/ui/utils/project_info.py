import streamlit as st
from models.project import Project

def render_project_info(project: Project):
    st.subheader("At a Glance")
    with st.container(horizontal=True):
        n_tasks = len(project) - len(project.phase_order)
        st.metric(
            label="Number of Tasks",
            value=n_tasks
        )
        st.space("stretch")

        st.metric(
            label="Planned Start",
            value=project.start_date.strftime("%b %d, %Y %I:%M %p").replace(" 0", " ")
        )

        st.space("stretch")

        st.metric(
            label="Planned End",
            value=project.end_date.strftime("%b %d, %Y %I:%M %p").replace(" 0", " ")
        )
        st.space("stretch")
        
        total_minutes = int(project.planned_duration.total_seconds() // 60)
        h, m = divmod(total_minutes, 60)
        s = f"{h}h {m}m"
        st.metric(
            label="Planned Duration",
            value=s
        )