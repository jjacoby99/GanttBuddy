import streamlit as st
import pandas as pd
from models.phase import Phase
from models.session import SessionModel

@st.dialog(f"Edit Phase")
def render_phase_edit(session):
    phases = session.project.phases

    if not phases:
        return
    
    phase_to_edit = st.selectbox(
        label=f"Select a phase to edit.",
        options=phases,
        format_func=lambda p: p.name if p else None,
        help="Select a phase to edit it's name or preceding task"
    )

    if not phase_to_edit:
        return
    
    phase_info = {
        "Name": phase_to_edit.name,
        "Preceding Phase": phase_to_edit.preceding_phase if phase_to_edit.preceding_phase else "-",
    }

    st.divider()
    c1, c2, c3 = st.columns(3)
    for key, val in phase_info.items():
        with c1:
            st.write(key)
        with c2:
            st.write(val)
        with c3:
            st.button(f"Edit",key=f"edit_phase_{key}")
        

