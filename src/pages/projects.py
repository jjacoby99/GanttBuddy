import streamlit as st
from zoneinfo import ZoneInfo

from logic.backend.guards import require_login
from logic.backend.project_list import get_projects
from logic.backend.api_client import fetch_project_snapshot
from logic.backend.import_project import snapshot_to_project
from logic.backend.project_permissions import resolve_project_access, store_project_access

from models.session import SessionModel
from models.project import Project, ProjectType
from models.plan_state import PlanState



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
    
    project, metadata = snapshot_to_project(proj_snapshot)
    st.session_state.session.project = project
    store_project_access(
        resolve_project_access(
            headers=st.session_state.auth_headers,
            project_id=selected_project_id,
            timezone=ZoneInfo(st.context.timezone),
            project_record=projects[selected_project_id],
        )
    )
    if project.project_type == ProjectType.MILL_RELINE and metadata is not None:
        st.session_state["reline_metadata"] = metadata 
        
    st.session_state["selected_project_id"] = selected_project_id
    st.session_state.plan_state = PlanState(project_id=selected_project_id)
    st.success(f"*{projects[selected_project_id]}* Loaded Successfully!")
    st.cache_data.clear()
    return


def render_project_explorer():
    require_login()
    projects = get_projects(st.session_state.get("auth_headers", {}))
    if len(projects) < 1:
        st.info(f":material/info: No accessible projects.")

        to_home = st.button(
            label="Return to home",
            type="primary"
        )

        if to_home:
            st.switch_page("pages/home.py")

        st.stop()

    with st.container(vertical_alignment="center", horizontal_alignment="center"):
        render_select_project(projects) 

    if "selected_project_id" in st.session_state: 
        st.switch_page("pages/plan.py")

if __name__ == "__main__":
    render_project_explorer()
