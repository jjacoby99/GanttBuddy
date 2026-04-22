import streamlit as st

from ui.add_crew import add_crew

def render_manage():
    st.subheader("Manage your operation")
    st.caption(f"Control your sites, crews, and projects")

    if st.button("Create A Crew"):
        add_crew()


if __name__ == "__main__":
    render_manage()