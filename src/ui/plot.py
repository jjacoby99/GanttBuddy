import streamlit as st
import plotly.express as px
import pandas as pd

def render_gantt(session):
    tasks = session.get_tasks()
    if not tasks:
        st.info("No tasks yet. Click **Add New Task** to begin.")
        return

    df = pd.DataFrame([t.to_dict() for t in tasks])

    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)
