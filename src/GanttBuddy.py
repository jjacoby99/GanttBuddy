import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from models.task import Task
from models.session import SessionModel
from models.ui_state import UIState
from ui.plot import render_gantt
from ui.tasks_view import render_tasks_table
from ui.settings_view import render_settings_view
from ui.sidebar import render_project_sidebar, render_project_buttons

st.set_page_config(layout="wide")

if "session" not in st.session_state:
    st.session_state.session = SessionModel()

if "ui" not in st.session_state:
    st.session_state.ui = UIState()

ui = st.session_state.ui

with st.sidebar:
    st.subheader(f"Project Explorer")
    render_project_sidebar(st.session_state.session)

if not st.session_state.session.project:
    st.info(f"Create or load a project to view.")
    st.stop()


with st.sidebar:
    render_project_buttons(st.session_state.session)

st.title(st.session_state.session.project.name)

save_col, _, _, settings_col = st.columns([2, 2, 10, 2])

with save_col:
    st.caption("Save")
    if st.button("💾", help="Save project to file"):
        proj_dict = st.session_state.session.project.to_dict()
        import json
        import os
        project_path = os.path.join(os.getcwd(),
                                    "projects",)
        os.makedirs(project_path, exist_ok=True)
        with open(os.path.join(project_path, st.session_state.session.project.name + ".json"), "w") as f:
            json.dump(proj_dict, f, default=str, indent=4)
            st.success("Project saved.")

with settings_col:
    st.caption("Settings")
    if st.button("🔧", help="View / Edit settings: work days, hours, holidays, etc."):
            st.session_state.ui.show_settings = True

if st.session_state.ui.show_settings:
    render_settings_view(st.session_state.session)
    st.session_state.ui.show_settings = False


if not st.session_state.session.project.phases:
    st.info(f"Add a phase to your project to begin.")
    st.stop()

if not st.session_state.session.project.has_task:
    st.info(f"Add a task to your project to begin.")
    st.stop()

task_col, plot_col = st.columns(2)

task_tab, plot_tab = st.tabs(["Task List", "Visualizer"])
with task_tab:
    render_tasks_table(st.session_state.session)

with plot_tab:
    render_gantt(st.session_state.session)

