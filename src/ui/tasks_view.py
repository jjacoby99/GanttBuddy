import pandas as pd
import streamlit as st

def render_tasks_table(session):
    phases = session.project.phases

    if not phases:
        st.info(f"Add a phase to {session.project.name} to view project planner")
        return

    for phase in phases:
        with st.expander(f"**{phase.name}**  "
                         f"({len(phase.tasks)} tasks)  "
                         f"— {phase.start_date or '—'} → {phase.end_date or '—'}",
                         expanded=True):
            # Header row
            cols = st.columns([3, 2, 2])
            cols[0].markdown("**Task**")
            cols[1].markdown("**Start**")
            cols[2].markdown("**Finish**")

            for t in phase.tasks:
                c = st.columns([3, 2, 2, 2])
                c[0].write(t.name)
                c[1].write(t.start_date)
                c[2].write(t.end_date)
                
                # optional per-task actions
                #ac = st.columns([1,1,6])
                #if ac[0].button("✏️ Edit", key=f"edit_{t.id}"):
                    #st.session_state.edit_task_id = t.id
                #if ac[1].button("🗑️ Delete", key=f"del_{t.id}"):
                    #session.project.remove_task(t.id); st.rerun()
    

     
