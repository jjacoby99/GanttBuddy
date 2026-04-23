import streamlit as st
from models.project import Project
from models.phase import Phase
from models.task import Task
from models.session import SessionModel
from models.input_models import RelineScope
from models.mill import ProjectType, ProjectBuilder, MillRelineBuilder, HVC_MILLS

import datetime as dt

from ui.mill_reline import render_mill_reline_inputs
from ui.crusher_rebuild import render_crusher_rebuild_inputs
from ui.utils.page_header import render_registered_page_header


def load_from_template():
    render_registered_page_header(
        "build",
        chips=["Mill relines", "Crusher rebuilds"],
    )
    template_options = [ProjectType.MILL_RELINE, ProjectType.CRUSHER_REBUILD]
    format_dict = {
        ProjectType.MILL_RELINE: "Mill Reline",
        ProjectType.CRUSHER_REBUILD: "Crusher Rebuild"
    }

    template_type = st.selectbox(
        "Select Template Type", 
        options=template_options,
        format_func=lambda x: format_dict[x],
        width=200
    )

    if template_type == ProjectType.MILL_RELINE:
        render_mill_reline_inputs()
        return

    if template_type == ProjectType.CRUSHER_REBUILD:
        render_crusher_rebuild_inputs()
        return
    

if __name__ == "__main__":
    load_from_template()
