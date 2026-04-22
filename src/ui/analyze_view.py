from logic.post_mortem import PostMortemAnalyzer

from models.project import Project
from models.phase import Phase
from models.task import Task
from models.session import SessionModel

import streamlit as st
import plotly.express as px

from typing import Literal
from pathlib import Path
from PIL import Image
import pandas as pd
import plotly.graph_objects as go

from io import BytesIO

from models.project import Project

from ui.utils.phase_delay_plot import generate_phase_delay_plot
from ui.report_export import render_report_export_dialog

UNIT_FACTORS = {
    "hours": 3600,
    "days": 86400,
    "weeks": 604800,
}

st.markdown(
    """
<style>
/* Custom look for SECONDARY buttons (HTML/CSS styling) */
div[data-testid="stButton"] > button[kind="secondary"] {
    border-radius: 14px;
    padding: 0.55rem 0.9rem;
    border: 1px solid rgba(0,0,0,0.12);
    background: linear-gradient(180deg, rgba(255,255,255,1), rgba(245,246,248,1));
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    font-weight: 600;
    transition: transform 120ms ease, box-shadow 120ms ease, border-color 120ms ease;
}

div[data-testid="stButton"] > button[kind="secondary"]:hover {
    transform: translateY(-1px);
    border-color: rgba(0,0,0,0.18);
    box-shadow: 0 6px 16px rgba(0,0,0,0.10);
}

div[data-testid="stButton"] > button[kind="secondary"]:disabled {
    opacity: 0.45;
    cursor: not-allowed;
    transform: none;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}
</style>
""",
    unsafe_allow_html=True,
)

def prev_phase():
        st.session_state.phase_idx = max(0, st.session_state.ui.analysis_phase_index - 1)

def next_phase():
    phases = len(st.session_state.session.project.phase_order)
    st.session_state.phase_idx = min(phases - 1, st.session_state.ui.analysis_phase_index + 1)

def render_analysis(session: SessionModel):
    if not session.project.has_actuals:
        st.info(f"Enter the actual durations of some tasks to analyze project performance.")
        return
    
    with st.container(horizontal=True):
        delay_units = st.selectbox(
            label="Delay units",
            options=list(UNIT_FACTORS.keys()),
            help="Change the y axis units for the phase delay analysis",
            width=100
        )

    fig = generate_phase_delay_plot(
        project=session.project,
        units=delay_units
    )

    st.plotly_chart(
        fig,
        width='stretch',
    )

    st.divider()
    st.subheader("Delays by phase")

    phase_idx = st.session_state.ui.analysis_phase_index
    pid = session.project.phase_order[phase_idx]
    phase = session.project.phases[pid]


    with st.container(horizontal=True, horizontal_alignment='center'):
        if st.button("←", type="secondary", on_click=prev_phase, disabled=(phase_idx == 0), key="analysis_left"):
            # reduce phase index by one
            st.session_state.ui.analysis_phase_index = max(0, st.session_state.ui.analysis_phase_index - 1)
            st.rerun()
        
        st.space(size="stretch")
        
        st.write(f"**Phase {phase_idx+1}. {phase.name}**")

        if st.button("→", type="secondary", on_click=next_phase, disabled=(phase_idx == len(session.project.phase_order) - 1), key="analysis_right"):
            st.session_state.ui.analysis_phase_index = min(len(session.project.phase_order) - 1, st.session_state.ui.analysis_phase_index + 1)
            st.rerun()
            
    phase_idx = st.session_state.ui.analysis_phase_index
    pid = session.project.phase_order[phase_idx]
    phase = session.project.phases[pid]
    
    phase_delays = PostMortemAnalyzer.analyze_phase_delays(
        phase=phase,
        n=-1
    )

    view = phase_delays[[
        "Task",
        "Delay",
        "Notes"
    ]]

    st.dataframe(
        view,
        width='stretch',
        hide_index=True,
    )

    with st.container(horizontal=True, horizontal_alignment='left'):
        st.info("Use the arrows to navigate between phases. Positive delay indicates the task took longer than planned.",
            width=730)
        st.space("stretch")

        if st.button(
            label="Export Report",
            icon=":material/insights:",
            help="Open export options for the Excel post-mortem workbook or the PowerPoint deck.",
        ):
            render_report_export_dialog(session)

