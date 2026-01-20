import streamlit as st
from models.project import Project
from models.phase import Phase
from models.task import Task
from models.session import SessionModel
from models.input_models import RelineScope
from models.project_types import ProjectType, ProjectBuilder, MillRelineBuilder, HVC_MILLS

import datetime as dt

@st.dialog(":material/dashboard_customize: Build from Template")
def load_from_template(session: SessionModel):
    template_options = [ProjectType.MILL_RELINE, ProjectType.CRUSHER_REBUILD]
    format_dict = {
        ProjectType.MILL_RELINE: "Mill Reline",
        ProjectType.CRUSHER_REBUILD: "Crusher Rebuild"
    }

    template_type = st.selectbox(
        "Select Template Type", 
        options=template_options,
        format_func=lambda x: format_dict[x]
    )

    if template_type == ProjectType.MILL_RELINE:
        with st.container(horizontal=True):
            selected_mill = st.selectbox(
                "Select Mill", 
                options=list(HVC_MILLS.keys()),
            )
            st.space("stretch")
            start_date = st.date_input(
                "Project Start Date", 
                value=dt.date.today()
            )

        mill = HVC_MILLS[selected_mill]

        tabs = st.tabs(["Feed End", "Shell", "Discharge End"])

        with tabs[0]:
            f1, f2 = st.columns(2)
            with f1:
                feed_head_segments = st.number_input(
                    "Feed head liner segments",
                    min_value=0,
                    step=1,
                    value=mill.n_fh,
                    help="Count of feed head liner segments/modules to remove and install.",
                )

                feed_head_fillers = st.number_input(
                    "Feed head fillers",
                    min_value=0,
                    step=1,
                    value=mill.n_fh_fillers
                )

                feed_head_grates = st.number_input(
                    "Feed head grates",
                    min_value=0,
                    step=1,
                    value=mill.n_fh_grates
                )
            with f2:
                t_fh = st.number_input(
                    "FH Liner time (min)",
                    min_value=1,
                    step=5,
                    value=10
                )

                t_fh_filler = st.number_input(
                    "FH Filler time (min)",
                    min_value=1,
                    step=5,
                    value=10
                )

                t_fh_grates = st.number_input(
                    "FH Grate time (min)",
                    min_value=1,
                    step=5,
                    value=10
                )
                
        with tabs[1]:
            s1, s2 = st.columns(2)
            with s1:       
                shell_rows = st.number_input(
                    "Shell rows to replace",
                    min_value=0,
                    step=1,
                    value=mill.n_shell,
                    help="Number of shell liner rows included in the reline.",
                )

                modules_per_shell_row = st.number_input(
                    "Modules (or liners) per shell row",
                    min_value=0,
                    step=1,
                    value=mill.modules_per_shell,
                    help="Number of shell pieces per row.",
                )
            
            with s2:
                t_shell_row = st.number_input(
                    "Shell Row time (min)",
                    min_value=1,
                    step=5,
                    value=10
                )

                t_inch = st.number_input(
                    "Mill Inch time (min)",
                    min_value=1,
                    step=1,
                    value=2
                )

            shell_total = shell_rows * modules_per_shell_row
            st.info(f"Computed shell modules total: {shell_total:,}")
        
        with tabs[2]:
            d1, d2 = st.columns(2)
            
            with d1:
                discharge_grate_rows = st.number_input(
                    "Discharge grate segments",
                    min_value=0,
                    step=1,
                    value=mill.n_discharge_grates,
                    help="Count of grate segments/modules to strip and install.",
                )

                pulp_lifter_rows = st.number_input(
                    "Pulp lifter segments",
                    min_value=0,
                    step=1,
                    value=mill.n_pulp_lifters,
                    help="Count of pulp lifter segments/modules to strip and install.",
                )

                st.space(size="small")
                replace_discharge_cone = st.toggle(
                    "Replace discharge cone",
                    value=True,
                    help="Enable if the discharge cone is part of the outage scope.",
                )
            
            with d2:
                t_dicharge_grate_row = st.number_input(
                    "Discharge Grate time (min)",
                    min_value=1,
                    step=5,
                    value=10
                )

                t_pulp_lifter_row = st.number_input(
                    "Pulp Lifter time (min)",
                    min_value=1,
                    step=5,
                    value=10
                )

                t_discharge_cone = st.number_input(
                    "Cone Removal time (min)", 
                    min_value=1,
                    value=4*60,
                    step=30
                )
                
        
        st.divider()

        candidate = RelineScope(
            start_date=dt.datetime.combine(start_date, dt.time(hour=7,minute=0,second=0)),
            t_inch=t_inch,
            feed_head_segments=feed_head_segments,
            t_fh=t_fh,
            feed_head_fillers=feed_head_fillers,
            t_fh_filler=t_fh_filler,
            feed_head_grates=feed_head_grates,
            t_fh_grates=t_fh_grates,
            shell_rows=shell_rows,
            t_shell_row=t_shell_row,
            modules_per_shell_row=modules_per_shell_row,
            discharge_grate_rows=discharge_grate_rows,
            t_discharge_grate_row=t_dicharge_grate_row,
            pulp_lifter_rows=pulp_lifter_rows,
            t_pulp_lifter_row=t_pulp_lifter_row,
            replace_discharge_cone=replace_discharge_cone,
            t_discharge_cone=t_discharge_cone
        )

        builder = MillRelineBuilder(mill=mill)

        if st.button("Create",icon=":material/add:", type='primary'):
            with st.spinner(
                text="Building project...",
                show_time=True
            ):
                project = builder.build(inputs=candidate)
            
            session.project = project
            st.success(f"Project '{project.name}' created from template.")
            st.rerun()
            return