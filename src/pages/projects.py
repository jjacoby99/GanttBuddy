import streamlit as st

from logic.backend.guards import require_login
from logic.backend.project_list import get_projects
from logic.backend.api_client import fetch_project_snapshot
from logic.backend.import_project import snapshot_to_project

from models.session import SessionModel
from models.project import Project



def render_select_project(projects: dict):
    st.subheader('Load a Project')
    with st.container(width="content", horizontal_alignment="center", vertical_alignment="center"):
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
                label=":material/calendar_month: Created",
                value=projects[selected_project_id]["created"].strftime("%b %d, %Y %I:%M")
            )

            st.metric(
                label=":material/calendar_month: Last Updated",
                value=projects[selected_project_id]["updated"].strftime("%b %d, %Y %I:%M")
            )

        load_proj = st.button(
            f"Load", 
            icon=":material/open_in_browser:", 
            type="primary"
        )
        
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
    return


def render_project_explorer():
    require_login()
    projects = get_projects(st.session_state.get("auth_headers", {}))

    with st.container(vertical_alignment="center", horizontal_alignment="center"):
        render_select_project(projects) 

    if "selected_project_id" in st.session_state: 
        st.switch_page("pages/workspace.py")

if __name__ == "__main__":
    render_project_explorer()