import streamlit as st
from datetime import date, timedelta
from models.task import Task
from models.phase import Phase
from models.session import SessionModel
from models.plan_state import PlanState
from ui.utils.constraints import build_constraint_target_labels, render_constraints_editor

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
    
    constraints = render_constraints_editor(
        key="add_phase_constraints",
        title=f"Add one or more predecessor rules for '{phase_name}'.",
        help_text="Choose the predecessor phase this phase depends on.",
        constraints=[],
        predecessor_kind="phase",
        labels_by_id=build_constraint_target_labels(
            (phase_id, session.project.phases[phase_id].name)
            for phase_id in session.project.phase_order
        ),
    )

    
    if st.button(label=f"Add '{phase_name or 'phase'}' to project", disabled=not phase_name):
        new_phase = Phase(
            name=phase_name,
            constraints=constraints,
        )

        plan_state.add_phase(phase_id=new_phase.uuid)
        session.project.add_phase(new_phase, position=position)

        st.info(f"Phase {phase_name} successfully added to {session.project.name}!")
        time.sleep(1)
        st.session_state.show_phase_dialog = False
        st.rerun()
