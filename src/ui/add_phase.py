import streamlit as st
from datetime import date, timedelta
from models.task import Task
from models.phase import Phase
import time
@st.dialog(f"Add a new phase to your project.")
def render_add_phase(session):
    
    phase_name = st.text_input(
        label="Enter the name of a project phase",
        placeholder="Construction",
        key="phase_name"
    )

    if not phase_name:
        return
    
    preceding_phase = None
    if session.project.phases:
        preceding_phase = st.selectbox(
            label="Select preceding phase (or nothing for the first phase)",
            placeholder="Admin",
            key=preceding_phase,
            options=session.project.phases,
            format_func=lambda t: "- None -" if t is None else t.name,
            help="Select the project phase that directly precedes {phase_name}"
        )

    
    if st.button(label=f"Add *{phase_name or 'phase'}* to project", disabled=not phase_name):
        new_phase = Phase(
            name=phase_name,
            tasks=[],
            preceding_phase=preceding_phase
        )

        session.project.add_phase(new_phase)

        st.info(f"Phase {phase_name} successfully added to {session.project.name}!")
        time.sleep(1)
        st.session_state.show_phase_dialog = False
        st.rerun()