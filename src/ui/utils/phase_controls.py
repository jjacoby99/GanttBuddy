import streamlit as st
from models.ui_state import UIState

def prev_phase():
        st.session_state.phase_idx = max(0, st.session_state.ui.analysis_phase_index - 1)

def next_phase():
    phases = len(st.session_state.session.project.phase_order)
    st.session_state.phase_idx = min(phases - 1, st.session_state.ui.analysis_phase_index + 1)

def prev_execution_phase():
        st.session_state.ui.execution_phase_index = max(0, st.session_state.ui.execution_phase_index - 1)

def next_execution_phase():
    phases = len(st.session_state.session.project.phase_order)
    st.session_state.ui.execution_phase_index = min(phases - 1, st.session_state.ui.execution_phase_index + 1)