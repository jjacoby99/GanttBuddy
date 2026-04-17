import streamlit as st

from logic.app_navigation import PageDefinition, build_navigation_sections, login_page_definition
from logic.backend.guards import is_admin
from logic.backend.login import get_current_user, is_logged_in, logout
from logic.state import initialize_session_state


st.set_page_config(
    page_title="GanttBuddy",
    layout="wide",
    initial_sidebar_state="auto",
)

initialize_session_state()


def _to_streamlit_page(page_definition: PageDefinition):
    kwargs = {"title": page_definition.title}
    if page_definition.icon:
        kwargs["icon"] = page_definition.icon
    return st.Page(page_definition.path, **kwargs)


if not is_logged_in():
    page = st.navigation([_to_streamlit_page(login_page_definition())])
    page.run()
    st.stop()


with st.sidebar:
    st.subheader("User")
    user_data = get_current_user(st.session_state.get("auth_headers"))
    with st.container(horizontal=True):
        st.caption(f":material/person: {user_data['email']}")
        st.space("stretch")
        if st.button(":material/logout: Logout", type="tertiary"):
            logout()


pages = {
    section_name: [_to_streamlit_page(page_definition) for page_definition in section_pages]
    for section_name, section_pages in build_navigation_sections(is_admin=is_admin()).items()
}

page = st.navigation(pages)
page.run()
