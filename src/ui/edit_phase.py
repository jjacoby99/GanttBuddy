import streamlit as st
from copy import deepcopy
from models.phase import Phase
from models.session import SessionModel
from models.plan_state import PlanState
from logic.backend.project_permissions import project_is_read_only
from ui.utils.constraints import build_constraint_target_labels, render_constraints_editor

@st.dialog(f"Edit Phase")
def render_phase_edit(session: SessionModel, phase: Phase, plan_state: PlanState):
    if project_is_read_only():
        st.info("This project is read-only, so phases cannot be edited.")
        return

    proj = session.project

    if not phase:
        return
    
    new_name = st.text_input(
        label="Name",
        value=phase.name
    )

    has_constraints = st.checkbox(
        label="Add predecessor constraints?",
        value=len(phase.constraints) > 0,
        help="Select to add dependencies that this phase has on earlier phases.",
    )
    constraints = []
    if has_constraints:
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
        if st.button(label="Save", disabled=project_is_read_only()):
            try:
                draft_project = deepcopy(session.project)
                draft_phase = draft_project.phases[phase.uuid]
                draft_phase.name = new_name
                draft_phase.constraints = constraints
                draft_project.resolve_schedule()
            except ValueError as exc:
                st.error(f"Unable to update phase: {exc}")
                st.stop()

            phase.name = new_name
            phase.constraints = constraints
            session.project.resolve_schedule()
            st.rerun()
        
        st.space("stretch")

        if st.button("Delete", disabled=project_is_read_only()):
            session.project.delete_phase(phase)
            plan_state.remove_phase(phase.uuid)
            st.rerun()

    


        

