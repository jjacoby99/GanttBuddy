import streamlit as st

from ui.plot import render_gantt, render_task_details
from ui.render_plan import render_plan

from ui.utils.workspace import render_workspace_buttons

render_workspace_buttons()


task_tab, plot_tab = st.tabs(
    [":material/list_alt: Plan", 
     ":material/view_timeline: Visualize"]
)

with task_tab:
    render_plan(st.session_state.session)


with plot_tab:
    render_gantt(st.session_state.session)
    st.divider()
    render_task_details(st.session_state.session)
