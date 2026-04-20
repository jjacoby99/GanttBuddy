import streamlit as st
from copy import deepcopy
from models.phase import Phase
from models.session import SessionModel
from models.plan_state import PlanState
from logic.backend.project_permissions import project_is_read_only
from ui.utils.constraints import build_constraint_target_labels, render_constraints_editor

import time
from datetime import datetime

@st.dialog(f"Add a new phase to your project.")
def render_add_phase(session: SessionModel, plan_state: PlanState, position: int | None = None):
    if project_is_read_only():
        st.info("This project is read-only, so phases cannot be added.")
        return

    phase_name = st.text_input(
        label="Name",
        placeholder="Construction",
        key="phase_name"
    )

    if not phase_name:
        return

    has_constraints = st.checkbox(
        label="Add predecessor constraints?",
        help="Select to add dependencies that this phase has on earlier phases.",
        value=False,
    )

    constraints = []
    if has_constraints:
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

    
    if st.button(label=f"Add '{phase_name or 'phase'}' to project", disabled=project_is_read_only() or not phase_name):
        new_phase = Phase(
            name=phase_name,
            constraints=constraints,
        )
        try:
            draft_project = deepcopy(session.project)
            draft_project.add_phase(new_phase, position=position)
            draft_project.resolve_schedule()
        except ValueError as exc:
            st.error(f"Unable to add phase: {exc}")
            st.stop()

        plan_state.add_phase(phase_id=new_phase.uuid)
        session.project.add_phase(new_phase, position=position)

        st.info(f"Phase {phase_name} successfully added to {session.project.name}!")
        time.sleep(1)
        st.session_state.show_phase_dialog = False
        st.rerun()
