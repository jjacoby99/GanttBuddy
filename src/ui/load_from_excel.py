import streamlit as st
from models.project import Project
from logic.load_project import ProjectLoader, ExcelProjectLoader, ExcelParameters, DataColumn

@st.dialog(":material/table_view: Import from Excel")
def load_from_excel() -> Project:

    st.caption("Import project schedule directly from a BTA Consulting template.")

    file = st.file_uploader(
        label="Select an Excel file",
        type=["xls", "xlsx"],
        help="Select a BTA Excel template file to import project data from"
    )

    if not file:
        return # user has not uploaded a file yet

    params = ExcelParameters(
        columns=[
            DataColumn(name="ACTIVITY", column=2),
            DataColumn(name="PLANNED DURATION (HOURS)", column=3),
            DataColumn(name="PLANNED START", column=4),
            DataColumn(name="PLANNED END", column=5),
            DataColumn(name="ACTUAL DURATION", column=7),
            DataColumn(name="ACTUAL START", column=8),
            DataColumn(name="ACTUAL END", column=9),
            DataColumn(name="NOTES", column=10),
            DataColumn(name="PREDECESSOR", column=11),
            DataColumn(name="UUID", column=12),
        ]
    )

    try:
        st.session_state.session.project = ExcelProjectLoader.load_excel_project(file, params)
    except (FileNotFoundError, ValueError) as e:
        st.error(str(e))
        return
    st.success(f"Project '{st.session_state.session.project.name}' imported from Excel.")
    st.rerun()