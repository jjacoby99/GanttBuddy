import streamlit as st
import pandas as pd
from models.phase import Phase
from models.task import Task
from models.session import SessionModel
import time

@st.dialog(f"Edit Task")
def render_task_edit(session, task: Task):
    phases = session.project.phases

    if not phases:
        return
    
    try:
        phase = session.project.find_phase(task)
    except ValueError as ve:
        st.error(str(ve))
        return
    
    task_dict = task.to_dict()
    del task_dict['Note']
    df = pd.DataFrame([task_dict])
    edited_df = st.data_editor(df)

    if st.button("Save"):
        edited_dict = edited_df.iloc[0].to_dict()

        edited_dict['Start'] = pd.to_datetime(edited_dict['Start'])
        edited_dict['Finish'] = pd.to_datetime(edited_dict['Finish'])
        new_task = Task.from_dict(edited_df.iloc[0].to_dict())
        session.project.update_task(phase=phase, old_task=task, new_task=new_task)

        st.success("Task updated.")
        time.sleep(3)
        st.rerun()


        

