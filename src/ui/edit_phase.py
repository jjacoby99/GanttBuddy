import streamlit as st
import pandas as pd
from models.phase import Phase
from models.session import SessionModel
from models.plan_state import PlanState
from ui.utils.constraints import build_constraint_target_labels, render_constraints_editor

@st.dialog(f"Edit Phase")
def render_phase_edit(session: SessionModel, phase: Phase, plan_state: PlanState):
    proj = session.project

    if not phase:
        return
    
    new_name = st.text_input(
        label="Phase name",
        value=phase.name
    )

    constraints = render_constraints_editor(
        key=f"{phase.uuid}_constraints",
        title=f"Predecessor rules for {new_name or phase.name}.",
        help_text="Choose the predecessor phase this phase depends on.",
        constraints=phase.constraints,
        predecessor_kind="phase",
        labels_by_id=build_constraint_target_labels(
            (pid, proj.phases[pid].name)
            for pid in proj.phase_order
            if pid != phase.uuid
        ),
    )
    
    with st.container(horizontal=True):
        if st.button(label="Save"):
            phase.name = new_name
            phase.constraints = constraints
            phase._sync_predecessor_ids()
            session.project.resolve_schedule()
            st.rerun()
        
        st.space("stretch")

        if st.button("Delete"):
            session.project.delete_phase(phase)
            plan_state.remove_phase(phase.uuid)
            st.rerun()

    


        

