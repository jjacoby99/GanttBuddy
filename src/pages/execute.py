import streamlit as st

from ui.forecast_view import render_forecast
from ui.execution_view import render_execution_view
from ui.delay_register import render_delay_register
from ui.utils.workspace import render_workspace_buttons


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