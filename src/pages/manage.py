import streamlit as st

from ui.add_crew import add_crew
from ui.add_site import add_site
from ui.utils.page_header import render_registered_page_header

def render_manage():
    render_registered_page_header("manage", chips=["Crews", "Sites", "Projects"])

    st.subheader("Crews")
    if st.button(":material/add_circle: Create A Crew"):
        add_crew()

    st.subheader("Sites")
    if st.button(":material/add_location: Create A Site"):
        add_site()


if __name__ == "__main__":
    render_manage()
