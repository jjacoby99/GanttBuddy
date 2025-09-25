import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from models.task import Task
from models.session import SessionModel
from ui.add_task import render_task_add
from ui.plot import render_gantt
from ui.tasks_view import render_tasks_table
from ui.settings_view import render_settings_view
from ui.sidebar import render_sidebar
from ui.add_phase import render_add_phase
st.set_page_config(layout="wide")

if "session" not in st.session_state:
    st.session_state.session = SessionModel()

if "show_settings_dialog" not in st.session_state:
    st.session_state.show_settings_dialog = False

if "show_task_dialog" not in st.session_state:
    st.session_state.show_add_dialog = False

if "show_phase_dialog" not in st.session_state:
    st.session_state.show_phase_dialog = False

with st.sidebar:
    st.subheader(f"Project Explorer")
    render_sidebar(st.session_state.session)

if not st.session_state.session.project:
    st.info(f"Create or load a project to view.")
    st.stop()

st.title(st.session_state.session.project.name)

proj_col, _, settings_col = st.columns([1, 10, 1])

with settings_col:
    if st.button("🔧", help="View / Edit settings: work days, hours, holidays, etc."):
            st.session_state.show_settings_dialog = True

if st.session_state.show_settings_dialog:
    render_settings_view(st.session_state.session)
    st.session_state.show_settings_dialog = False

with proj_col:
    if st.button("Add Phase"):
        st.session_state.show_phase_dialog = True

if st.session_state.show_phase_dialog:
    render_add_phase(st.session_state.session)
    st.session_state.show_phase_dialog = False

if st.session_state.session.project.phases:
    # Open dialog
    if st.button("Add New Task", key="add_task_button"):
        st.session_state.show_add_dialog = True
else:
    st.info(f"Add a phase to your project to begin.")
    st.stop()



if st.session_state.show_add_dialog:
    render_task_add(st.session_state.session)
    st.session_state.show_add_dialog = False

task_col, plot_col = st.columns(2)

task_tab, plot_tab = st.tabs(["Task List", "Visualizer"])
with task_tab:
    render_tasks_table(st.session_state.session)

with plot_tab:
    render_gantt(st.session_state.session)

