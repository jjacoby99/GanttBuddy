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
    
    task_dict = task.to_dict()
    
    df = pd.DataFrame([task_dict])
    df = df.drop(["Note", "preceding_task"], axis=1)

    precdeding_task_options = ["None"] + [t for t in phase.tasks if t.name != task.name]
    
    default_preceding_task = precdeding_task_options.index(task.preceding_task) if task.preceding_task else None
    preceding_task = st.selectbox(
        label=f"Preceding Task",
        options=precdeding_task_options,
        format_func=lambda t: t.name if not isinstance(t, str) else t,
        index=default_preceding_task,
        help=f"Select the task that comes directly before **{task.name}** chronologically."
    )
    
    if st.toggle(label="Move task"):
        following_task = st.selectbox(
            label="Move task before",
            options = [t for t in phase.tasks if not t in [task, preceding_task]] + ["Move to Phase end"],
            format_func = lambda t: t.name if not isinstance(t, str) else t,
            help=f"Select the task that follows **{task.name}**"
        )


    st.caption("Task Parameters")
    edited_df = st.data_editor(
        df,
        use_container_width=True
    )
    if st.button("Save"):
        edited_dict = edited_df.iloc[0].to_dict()

        edited_dict['Start'] = pd.to_datetime(edited_dict['Start'])
        edited_dict['Finish'] = pd.to_datetime(edited_dict['Finish'])
        edited_dict['preceding_task'] = preceding_task if preceding_task != "None" else None
        
        new_task = Task.from_dict(edited_dict)

        session.project.update_task(
            phase=phase, 
            old_task=task, 
            new_task=new_task
        )

        st.success("Task updated.")
        time.sleep(3)
        st.rerun()


        

