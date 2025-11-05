import streamlit as st
import pandas as pd
from models.phase import Phase
from models.task import Task
from models.session import SessionModel
import time

@st.dialog(f"Edit Task")
def render_task_edit(session, phase: Phase, task: Task):
    phases = session.project.phases

    if not phases:
        return
    
    edited_task_name = st.text_input(
        label="Edit name",
        value=task.name if task.name else ""
    )

    task_dict = task.to_dict()
    planned_df = pd.DataFrame([task_dict])
    actual_df = pd.DataFrame([task_dict])

    planned_df = planned_df.drop(["Task", "Note", "uuid", "phase_id", "predecessor_ids", "Actual_Start", "Actual_Finish"], axis=1)
    actual_df = actual_df.drop(["Task", "Note", "uuid", "phase_id", "predecessor_ids", "Start", "Finish"], axis=1)
    
    precdeding_task_options = ["None"] + [t for t in phase.tasks.values() if t.name != task.name]
    
    default_predecessors = [phase.tasks[id] for id in task.predecessor_ids]

    predecessors = st.multiselect(
        label=f"Preceding Tasks",
        options=[val for _, val in phase.tasks.items()if val.name != task.name],
        default=default_predecessors,
        format_func=lambda t: t.name,
        help=f"Select tasks that must finish before {task.name} begins."
    )

    st.caption("Edit Task Plan")
    edited_planned_df = st.data_editor(
        planned_df,
        use_container_width=True,
        hide_index=True
    )
    
    st.caption("Edit actual start / end")
    edited_actual_df = st.data_editor(
        actual_df,
        hide_index=True
    )
    if st.button("Save"):
        edited_dict = edited_planned_df.iloc[0].to_dict()

        actual_edited_dict = edited_actual_df.iloc[0].to_dict()

        edited_dict = edited_dict | actual_edited_dict # merge 
        edited_dict['Start'] = pd.to_datetime(edited_dict['Start'])
        edited_dict['Finish'] = pd.to_datetime(edited_dict['Finish'])
        edited_dict['Actual_Start'] = pd.to_datetime(edited_dict['Actual_Start'])
        edited_dict['Actual_Finish'] = pd.to_datetime(edited_dict['Actual_Finish'])
        edited_dict['Task'] = edited_task_name
        edited_dict['predecessor_ids'] = [p.uuid for p in predecessors]

        new_task = Task.from_dict(edited_dict)

        session.project.update_task(
            phase=phase, 
            old_task=task, 
            new_task=new_task
        )

        st.success("Task updated.")
        time.sleep(1)
        st.rerun()


        

