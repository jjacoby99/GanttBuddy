import streamlit as st

from ui.plot import render_gantt, render_task_details
from ui.settings_view import render_settings_view
from ui.utils.project_buttons import render_project_buttons
from ui.forecast_view import render_forecast
from ui.compact_buttons import use_compact_buttons
from ui.analyze_view import render_analysis
from ui.edit_project import render_edit_project
from ui.render_plan import render_plan
from ui.execution_view import render_execution_view

from logic.backend.login import  get_current_user, reset_auth
from logic.backend.api_client import save_project

from PIL import Image
from pathlib import Path


@st.cache_data
def load_image(path: str):
    return Image.open(path)


use_compact_buttons()

ui = st.session_state.ui

with st.sidebar:
    st.subheader("User")
    user_data = get_current_user(st.session_state.get("auth_headers"))
    with st.container(horizontal=True):
        
        st.caption(f":material/person: {user_data['email']}")
        st.space("stretch")
        if st.button(":material/logout: Logout", type="tertiary"):
            reset_auth()
            st.rerun()
        
if st.session_state.session.project is None:

    with st.container(horizontal_alignment="center"):
        st.info(f"Create or load a project to view.", icon=":material/info:", width=270)
        path = Path(__file__).parent.parent.resolve() / "assets" / "ganttbuddy.png"
        st.space("large")
        st.image(load_image(path))
        st.stop()


with st.sidebar:
    render_project_buttons(st.session_state.session)

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
            st.success("Project saved to server.")
        except Exception as e:
            st.error(f"Failed to save project to server: {e}")
        
    st.space("stretch")
    if st.button("🔧", help="View / Edit settings: work days, hours, holidays, etc."):
        st.session_state.ui.show_settings = True

if st.session_state.ui.show_settings:
    render_settings_view(st.session_state.session)
    st.session_state.ui.show_settings = False

# if not st.session_state.session.project.phases:
#     st.info(f"Add a phase to your project to begin.")
#     st.stop()

# if not st.session_state.session.project.has_task:
#     st.info(f"Add a task to your project to begin.")
#     st.stop()


task_tab, execute_tab, plot_tab, forecast_tab, analyze_tab = st.tabs(
    [":material/list_alt: Plan", 
     ":material/play_circle: Execute", 
     ":material/view_timeline: Visualize", 
     ":material/trending_up: Forecast", 
     ":material/query_stats: Analyze"]
)

with task_tab:
    render_plan(st.session_state.session)

with execute_tab:
    render_execution_view(st.session_state.session)

with plot_tab:
    render_gantt(st.session_state.session)
    st.divider()
    render_task_details(st.session_state.session)

with forecast_tab:
    render_forecast(st.session_state.session)

with analyze_tab:
    render_analysis(st.session_state.session)
