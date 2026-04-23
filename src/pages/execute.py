import streamlit as st

from ui.forecast_view import render_forecast
from ui.execution_view import render_execution_view
from ui.utils.page_header import render_registered_page_header
from ui.utils.workspace import render_workspace_buttons

project = st.session_state.session.project
render_registered_page_header("execute", chips=[project.name] if project is not None else [])

render_workspace_buttons()

execute_tab, forecast_tab = st.tabs(
    [
     ":material/play_circle: Execute", 
     ":material/trending_up: Forecast", 
    ])


with execute_tab:
    render_execution_view(st.session_state.session)

with forecast_tab:
    render_forecast(st.session_state.session)
