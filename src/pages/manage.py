import streamlit as st

from ui.add_crew import add_crew
from ui.utils.page_header import render_registered_page_header

def render_manage():
    render_registered_page_header("manage", chips=["Crews", "Sites", "Projects"])

    if st.button("Create A Crew"):
        add_crew()


if __name__ == "__main__":
    render_manage()
