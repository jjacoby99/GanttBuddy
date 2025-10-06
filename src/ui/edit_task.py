import streamlit as st
import pandas as pd
from models.phase import Phase
from models.task import Task
from models.session import SessionModel


@st.dialog(f"Edit Task")
def render_task_edit(session, task: Task):
    phases = session.project.phases

    if not phases:
        return
    
    phase = st.selectbox(
        label=f"Select a phase.",
        options=phases,
        format_func=lambda p: p.name if p else None,
        help="Select a phase containing a task to edit."
    )

    if not phase:
        return
    
    try:
        phase_idx = session.project.get_phase_index(phase)
    except RuntimeError:
        st.error(f"Project {session.project.name} doesn't contain any phases.")
        return
    except ValueError:
        st.error(f"Project {session.project.name} doesn't contain a {phase.name} phase.")

    task_list = session.project.phases[phase_idx].tasks

    if not task_list:
        st.info(f"Selected phase **{phase}** does not contain any tasks.")
        return
    
    st.divider()
    with st.expander:
        c1, c2, c3 = st.columns(3)       
        with c1:
            st.subheader("Task Name")

        with c2:
            st.subheader("Start Date")
        
        with c3:
            st.subheader("End Date")
        for i, task in enumerate(task_list, start=1):

            with c1:
                st.write(f"{i}. {task.name}")
            with c2:
                st.write(f"{task.start_date}")
            with c3:
                st.write(f"{task.end_date}")


        

