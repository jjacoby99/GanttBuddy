import streamlit as st

from logic.backend.guards import require_login
from logic.backend.api_client import fetch_project_snapshot
from logic.backend.import_project import snapshot_to_project
from logic.backend.project_list import get_projects



def render_recent_projects(projects: dict):
    st.subheader("Recent Projects")

    with st.container(width="content",horizontal=True):
        for pid in list(projects.keys())[:3]:
            with st.container(border=True, horizontal_alignment="center", vertical_alignment="center", width="content"):
                st.subheader(projects[pid].get("name", "unnamed").split('\n')[0])

                st.metric(
                    label=":material/calendar_month: Last Updated",
                    value=projects[pid].get("updated").strftime("%b %d, %Y %I:%M"),
                    border=True
                )

                load_proj = st.button(
                    label=f"Load", 
                    icon=":material/open_in_browser:", 
                    type="primary", 
                    key=f"load_{pid}"
                )

                if load_proj:
                    st.session_state["selected_project_id"] = pid
                    
                    try:
                        proj_snapshot = fetch_project_snapshot(
                            project_id=pid,
                            headers=st.session_state.auth_headers
                        )
                        st.session_state.session.project = snapshot_to_project(proj_snapshot)
                    except Exception as e:
                        st.error(f"Error loading project *{projects[pid]}*")
                        st.stop()
            
            st.space("stretch")


def render_feed():
    projects = get_projects(st.session_state.get("auth_headers", {}))
    render_recent_projects(projects)

if __name__ == "__main__":
    require_login()
    render_feed()
    
    