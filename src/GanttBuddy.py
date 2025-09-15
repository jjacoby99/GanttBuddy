import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from lib.task import Task
from lib.session import SessionModel
from ui.add_task import render_task_add
from ui.plot import render_gantt
from ui.tasks_view import render_tasks_table
from ui.sidebar import render_sidebar

st.set_page_config(layout="wide")

# Initialize once
if "session" not in st.session_state:
    st.session_state.session = SessionModel()

if "show_add_dialog" not in st.session_state:
    st.session_state.show_add_dialog = False



with st.sidebar:
    st.subheader(f"Project")
    render_sidebar(st.session_state.session)

if not st.session_state.session.project:
    st.info(f"Create or load a project to view.")
    st.stop()
    st.title("GanttBuddy")

st.title(st.session_state.session.project.name)
# Open dialog
if st.button("Add New Task", key="add_task_button"):
    st.session_state.show_add_dialog = True

# Render dialog when flagged
if st.session_state.show_add_dialog:
    render_task_add(st.session_state.session)

task_col, plot_col = st.columns(2)
with task_col:
    render_tasks_table(st.session_state.session)

# Plot
with plot_col:
    render_gantt(st.session_state.session)
