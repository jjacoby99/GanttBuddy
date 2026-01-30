import streamlit as st

from models.project import Project

from logic.backend.project_list import get_projects
from logic.backend.api_client import fetch_project_snapshot
from logic.backend.import_project import snapshot_to_project

@st.dialog(f":material/open_in_browser: Load Saved Project")
def render_load_project() -> Project:
    try:
        projects = get_projects(st.session_state.auth_headers)
    except Exception as e:
        st.error(f"Error fetching saved projects: {e}")
        st.stop()
    
    load_proj = False
    
    selected_project_id = st.selectbox(
        label="Project",
        options=[pid for pid in projects.keys()],
        format_func=lambda pid: projects[pid]["name"],
        help="Select a saved project to load."
    )

    if projects[selected_project_id].get("description"):
        st.caption("Description")
        st.write(f"{projects[selected_project_id]["description"]}")

    with st.container(horizontal=True):
        st.metric(
            label="Created",
            value=projects[selected_project_id]["created"].strftime("%b %d, %Y %I:%M")
        )

        st.metric(
            label="Last Updated",
            value=projects[selected_project_id]["updated"].strftime("%b %d, %Y %I:%M")
        )

    if st.button(f"Load", icon=":material/open_in_browser:", type="primary"):
        load_proj = True
    
    if not load_proj:
        st.stop()

    try:
        proj_snapshot = fetch_project_snapshot(
            project_id=selected_project_id,
            headers=st.session_state.auth_headers
        )
    except Exception as e:
        st.error(f"Error loading project *{projects[selected_project_id]}*")
        st.stop()
    
    st.session_state.session.project = snapshot_to_project(proj_snapshot)
    st.session_state["selected_project_id"] = selected_project_id
    st.success(f"*{projects[selected_project_id]}* Loaded Successfully!")
    st.rerun()