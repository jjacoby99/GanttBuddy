import pandas as pd
import streamlit as st

def render_tasks_table(session):
    tasks = session.get_tasks()
    if not tasks:
        return
    
    dict_arr = [t.to_dict() for t in tasks]

    df = pd.DataFrame(dict_arr)

    edited_df = st.data_editor(
        df,
        num_rows = "dynamic"
    )

     
