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

def generate_phase_delay_plot(
    project: Project,
    units: Literal["hours", "days", "weeks"] = "hours",
):
    """
    Generate a post-mortem chart of per-phase delay and cumulative delay.
    Units can be one of: "hours", "days", "weeks".
    Returns a Plotly Figure.
    """
    import textwrap  # local import to keep the rest of your file untouched

    def _wrap_label(label: str, width: int = 22, max_lines: int = 3) -> str:
        """
        Wrap label for Plotly ticks using <br>.
        Caps number of lines so super-long names don't make the chart too tall.
        """
        if not label:
            return ""
        lines = textwrap.wrap(str(label), width=width)
        if len(lines) <= max_lines:
            return "<br>".join(lines)

        kept = lines[:max_lines]
        # Truncate final line with ellipsis
        if len(kept[-1]) >= 3:
            kept[-1] = kept[-1][:-3] + "..."
        else:
            kept[-1] = kept[-1] + "..."
        return "<br>".join(kept)

    # Validate
    if units not in UNIT_FACTORS:
        raise ValueError(f"Invalid units '{units}'. Expected one of {list(UNIT_FACTORS.keys())}.")

    phase_ids = project.phase_order
    if not phase_ids:
        return go.Figure()

    seconds_per_unit = UNIT_FACTORS[units]
    rows = []

    phase_ids = project.phase_order

    for pid in phase_ids:
        phase = project.phases[pid]

        planned = phase.planned_duration
        actual = phase.actual_duration

        # Skip phases without required time data
        if planned is None or actual is None:
            continue

        # Phase delay
        delay_td = actual - planned
        delay_val = delay_td.total_seconds() / seconds_per_unit

        # Cumulative delay at this phase
        if phase.actual_end is None or phase.end_date is None:
            cumulative = None
        else:
            cum_td = phase.actual_end - phase.end_date
            cumulative = cum_td.total_seconds() / seconds_per_unit

        rows.append(
            {
                "phase_name": phase.name,
                "delay": delay_val,
                "cumulative": cumulative,
            }
        )

    if not rows:
        return go.Figure()

    df = pd.DataFrame(rows)

    # NEW: wrapped x-axis labels (display) + keep full names for hover
    df["phase_label"] = df["phase_name"].apply(lambda s: _wrap_label(s, width=22, max_lines=3))

    # Color scheme similar to Excel inspiration
    bar_colors = ["#e67e22"] * len(df)  # orange bars
    line_color = "#2c3e50"              # dark line

    fig = go.Figure()

    # Bar plot
    fig.add_trace(
        go.Bar(
            x=df["phase_label"],
            y=df["delay"],
            name=f"Phase Delay ({units})",
            marker=dict(color=bar_colors),
            customdata=df["phase_name"],  # full name for hover
            hovertemplate="<b>%{customdata}</b><br>Phase Delay: %{y:.1f} " + units + "<extra></extra>",
        )
    )

    # Line plot
    fig.add_trace(
        go.Scatter(
            x=df["phase_label"],
            y=df["cumulative"],
            name=f"Cumulative Delay ({units})",
            mode="lines+markers",
            line=dict(color=line_color, width=3),
            marker=dict(size=8, color=line_color),
            customdata=df["phase_name"],  # full name for hover
            hovertemplate="<b>%{customdata}</b><br>Cumulative: %{y:.1f} " + units + "<extra></extra>",
        )
    )

    # Add BTA logo
    logo_path = Path("src/assets/bta_logo.png")
    if logo_path.exists():
        try:
            logo = Image.open(logo_path)
            fig.add_layout_image(
                dict(
                    source=logo,
                    xref="paper", yref="paper",
                    x=0.925, y=0.85,
                    sizex=0.15, sizey=0.15,
                    xanchor="left", yanchor="bottom",
                    layer="above"
                )
            )
        except Exception:
            pass

    # Style & layout
    fig.update_layout(
        title=f"{project.name} – Delay By Phase",
        title_font=dict(size=26, color="#2c3e50"),
        barmode="group",
        template="plotly_white",
        xaxis_title="Phase",
        yaxis_title=f"Delay ({units})",
        hovermode="x unified",
        margin=dict(l=80, r=110, t=100, b=80),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=-0.3,
            xanchor="left", x=0.5,
        ),
    )

    # Aesthetic tweaks like Excel inspiration
    fig.update_xaxes(
        tickangle=0,
        showgrid=True,
        gridcolor="#d0d8e8",
        linecolor="#7f8c8d",
        automargin=True,  # NEW: let Plotly expand margins if wrapped labels need room
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="#d0d8e8",
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor="#95a5a6",
    )

    # Light gradient background (subtle, Excel-like)
    fig.update_layout(
        plot_bgcolor="rgba(240,248,255,1)",
        paper_bgcolor="white",
    )

    return fig

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
        use_container_width=True,
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

    prepare_post_mortem = st.checkbox(
        label="Prepare post mortem report",
        value=False,
        help="Select to begin the preparation of a post mortem report for download."
    )

    if prepare_post_mortem:
        with st.spinner(f"Preparing report..."):
            wb = PostMortemAnalyzer.write_post_mortem(project=session.project, n=-1)
            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)

    with st.container(horizontal=True, horizontal_alignment='left'):
        st.info("Use the arrows to navigate between phases. Positive delay indicates the task took longer than planned.",
            width=730)
        st.space("stretch")

        if prepare_post_mortem:
            st.download_button(
                label="Performance Report",
                icon=":material/insights:",
                data=buffer,
                file_name=f"{session.project.name}_phase_delay.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                disabled=not prepare_post_mortem
            )

