import streamlit as st

from ui.signals_view import render_signals_view
from ui.utils.workspace import render_workspace_buttons


render_workspace_buttons()
render_signals_view(st.session_state.session)
