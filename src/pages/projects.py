import streamlit as st

from logic.backend.guards import require_login
from logic.backend.project_list import get_projects
from ui.load_project import load_project_into_session, render_project_browser


def render_project_explorer() -> None:
    require_login()

    selected_project_id = render_project_browser(key_prefix="page_project_browser", full_page=True)
    include_closed = st.session_state.get("page_project_browser_include_closed", False)
    projects = get_projects(st.session_state.get("auth_headers", {}), include_closed=include_closed)

    if not projects:
        st.info(":material/info: No accessible projects.")
        if st.button("Return to home", type="primary"):
            st.switch_page("pages/home.py")
        st.stop()

    if selected_project_id is None:
        st.stop()

    load_project_into_session(selected_project_id, projects[selected_project_id])
    st.switch_page("pages/plan.py")


if __name__ == "__main__":
    render_project_explorer()
