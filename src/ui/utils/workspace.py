import streamlit as st

from ui.settings_view import render_settings_view
from ui.sidebar import render_project_buttons
from ui.compact_buttons import use_compact_buttons
from ui.edit_project import render_edit_project

from logic.backend.login import get_current_user, reset_auth
from logic.backend.api_client import save_project

import time

from PIL import Image
from pathlib import Path


@st.cache_data
def load_image(path: str):
    return Image.open(path)

def render_workspace_buttons():
    use_compact_buttons()

    ui = st.session_state.ui
            
    if st.session_state.session.project is None:

        with st.container(horizontal_alignment="center"):
            st.info(f"Create or load a project to view.", icon=":material/info:", width=270)
            path = Path(__file__).parent.parent.resolve() / "assets" / "ganttbuddy.png"
            st.space("large")
            st.image(load_image(path))
            st.stop()


    # with st.sidebar:
    #     render_project_buttons(st.session_state.session)

    with st.container(horizontal=True):
        st.title(st.session_state.session.project.name)
        st.space("stretch")

        if st.button(f"📝 Edit Project"):
            ui.show_edit_project = True

    if ui.show_edit_project:
        render_edit_project(st.session_state.session)
        ui.show_edit_project = False

    with st.container(horizontal=True):
        if st.button("💾", help="Save project to file"):
            try:
                save_project(st.session_state.session.project, headers=st.session_state.get("auth_headers"))
                success = st.success(":material/check: Project saved to server.", width=210)
                time.sleep(3)
                success.empty()
            except Exception as e:
                st.error(f"Failed to save project to server: {e}")
            
        st.space("stretch")
        if st.button("🔧", help="View / Edit settings: work days, hours, holidays, etc."):
            st.session_state.ui.show_settings = True

    if st.session_state.ui.show_settings:
        render_settings_view(st.session_state.session)
        st.session_state.ui.show_settings = False