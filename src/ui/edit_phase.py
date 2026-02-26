import streamlit as st
import pandas as pd
from models.phase import Phase
from models.session import SessionModel
from models.plan_state import PlanState

@st.dialog(f"Edit Phase")
def render_phase_edit(session: SessionModel, phase: Phase, plan_state: PlanState):
    proj = session.project

    if not phase:
        return
    
    new_name = st.text_input(
        label="Phase name",
        value=phase.name
    )

    predecessor_options = [pid for pid in proj.phase_order if pid != phase.uuid]

    new_predecessors = st.multiselect(
        label="Predecessor phases",
        options=predecessor_options,
        format_func=lambda pid: proj.phases[pid].name,
        help=f"Select phases that must finish before {new_name} begins.",
        default=phase.predecessor_ids
    )
    
    with st.container(horizontal=True):
        if st.button(label="Save"):
            phase.name = new_name
            phase.predecessor_ids = new_predecessors
            st.rerun()
        
        st.space("stretch")

        if st.button("Delete"):
            session.project.delete_phase(phase)
            plan_state.remove_phase(phase.uuid)
            st.rerun()

    


        

