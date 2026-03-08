import streamlit as st
from datetime import date, timedelta
from models.task import Task
from models.phase import Phase
from models.session import SessionModel
from models.plan_state import PlanState

import time
from datetime import datetime

@st.dialog(f"Add a new phase to your project.")
def render_add_phase(session: SessionModel, plan_state: PlanState, position: int | None = None):
    
    phase_name = st.text_input(
        label="Enter the name of a project phase",
        placeholder="Construction",
        key="phase_name"
    )

    if not phase_name:
        return
    
    predecessor_ids = []
    if session.project.phases:
        predecessor_options = [None] + [id for id in session.project.phase_order]
        predecessor_ids = st.multiselect(
            label=f"Select phases that precede '{phase_name}'",
            placeholder="Admin",
            options=predecessor_options,
            format_func=lambda id: "- None -" if id is None else session.project.phases[id].name,
            help=F"Select the project phases that directly precede {phase_name}"
        )
    
    # if user inputs predecessors, and at least one has an end date (task has been added)
    # give them info on when the new phase can start at at the earliest
    if predecessor_ids and session.project.end_date:        
        earliest_start = max(session.project.phases[id].end_date for id in predecessor_ids)
        st.info(f"Based on predecessors, the earliest start for '{phase_name}' is **{earliest_start.strftime("%Y-%m-%d %H:%M")}**")

    
    if st.button(label=f"Add '{phase_name or 'phase'}' to project", disabled=not phase_name):
        new_phase = Phase(
            name=phase_name,
            predecessor_ids=predecessor_ids
        )

        plan_state.add_phase(phase_id=new_phase.uuid)
        session.project.add_phase(new_phase, position=position)

        st.info(f"Phase {phase_name} successfully added to {session.project.name}!")
        time.sleep(1)
        st.session_state.show_phase_dialog = False
        st.rerun()