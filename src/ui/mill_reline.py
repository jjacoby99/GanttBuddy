import streamlit as st
from models.project import Project
from models.phase import Phase
from models.task import Task
from models.input_models import RelineScope, FeedHeadInputs, ShellInputs, DischargeInputs
from models.mill import ProjectType, ProjectBuilder, MillRelineBuilder, HVC_MILLS, Mill
from models.shift_schedule import ShiftAssignment

from logic.backend.api_client import fetch_sites, fetch_mills, fetch_site
from logic.backend.crews.fetch_crews import get_crews

import datetime as dt
from zoneinfo import ZoneInfo

from ui.shift_config import render_shift_assignment_table, render_tz_info
from ui.project_metadata import render_reline_metadata_form
from ui.shift_definition import render_shift_definition

def render_feed_end(mill: Mill, strip_install: bool, n_cols: int) -> FeedHeadInputs:
    fh_cols = st.columns(n_cols, border=True, width="stretch")

    with fh_cols[0]:
        st.subheader(":material/construction: Stripping")
        feed_head_segments = st.number_input(
            "Liner segments",
            min_value=0,
            step=1,
            value=mill.n_fh,
            help="Count of feed head liner segments/modules to remove and install.",
            width=150
        )

        feed_head_fillers = st.number_input(
            "Fillers",
            min_value=0,
            step=1,
            value=mill.n_fh_fillers,
            width=150
        )

        feed_head_grates = st.number_input(
            "Grates",
            min_value=0,
            step=1,
            value=mill.n_fh_grates,
            width=150
        )

    with fh_cols[1]:
        st.subheader(":material/access_time: Stripping time (min)")
        t_fh = st.number_input(
            "Liners",
            min_value=1,
            step=5,
            value=10,
            width=150,
            key="fh_strip_time"
        )

        t_fh_filler = st.number_input(
            "Fillers",
            min_value=1,
            step=5,
            value=10,
            width=150,
            key="fh_filler_strip_time"
        )

        t_fh_grates = st.number_input(
            "Grates",
            min_value=1,
            step=5,
            value=10,
            width=150,
            key="fh_grate_strip_time"
        )

    if not strip_install:
        with fh_cols[2]:
            st.subheader(":material/construction: Installation")
            feed_head_segments_install = st.number_input(
                "Liner segments",
                min_value=0,
                step=1,
                value=mill.n_fh,
                help="Count of feed head liner segments/modules to remove and install.",
                width=150,
                key="n_fh_liner_install"
            )

            feed_head_fillers_install = st.number_input(
                "Fillers",
                min_value=0,
                step=1,
                value=mill.n_fh_fillers,
                width=150,
                key="n_fh_filler_install"
            )

            feed_head_grates_install = st.number_input(
                "Grates",
                min_value=0,
                step=1,
                value=mill.n_fh_grates,
                width=150,
                key="n_fh_grates_install"
            )
    
    with fh_cols[len(fh_cols)-1]:
        st.subheader(":material/access_time: Install time (min)")
        t_fh_install = st.number_input(
            "Liners",
            min_value=1,
            step=5,
            value=10,
            width=150,
            key="fh_install_time"
        )

        t_fh_filler_install = st.number_input(
            "Fillers",
            min_value=1,
            step=5,
            value=10,
            width=150,
            key="fh_filler_install_time"
        )

        t_fh_grates_install = st.number_input(
            "Grates",
            min_value=1,
            step=5,
            value=10,
            width=150,
            key="fh_grate_install_time"
        )

    return FeedHeadInputs(
        n_liner_strip = feed_head_segments,
        n_filler_strip = feed_head_fillers,
        n_grates_strip = feed_head_grates,
        t_liner_strip = t_fh,
        t_filler_strip = t_fh_filler,
        t_grates_strip = t_fh_grates,
        t_liner_install = t_fh_install,
        t_filler_install = t_fh_filler_install,
        t_grates_install = t_fh_grates_install,
        n_liner_install = feed_head_segments_install if not strip_install else feed_head_segments, 
        n_filler_install = feed_head_fillers_install if not strip_install else feed_head_fillers,
        n_grates_install = feed_head_grates_install if not strip_install else feed_head_grates,
    )

def render_shell(mill: Mill, strip_install: bool, n_cols: int) -> ShellInputs:
    shell_cols = st.columns(n_cols, border=True, width="stretch")
    
    with shell_cols[0]:
        st.subheader(":material/construction: Stripping")       
        strip_shell_rows = st.number_input(
            "Shell rows",
            min_value=0,
            step=1,
            value=mill.n_shell,
            help="Number of shell liner rows included in the reline.",
            width=150,
        )

        strip_modules_per_shell_row = st.number_input(
            "Liners per shell row",
            min_value=0,
            step=1,
            value=mill.modules_per_shell,
            help="Number of shell pieces per row.",
            width=150
        )
        strip_shell_total = strip_shell_rows * strip_modules_per_shell_row
        st.info(f":material/info: Shell Liners to be stripped: {strip_shell_total:}", width=250)
    
    with shell_cols[1]:
        st.subheader(":material/access_time: Stripping time (min)")
        t_strip_shell_row = st.number_input(
            "Strip time (min)",
            min_value=1,
            step=5,
            value=10,
            width=150,
            key="shell_row_strip_time"
        )

    if not strip_install:
        with shell_cols[2]:
            st.subheader(":material/construction: Installation")
            install_shell_rows = st.number_input(
                "Shell rows",
                min_value=0,
                step=1,
                value=mill.n_shell,
                help="Number of shell liner rows included in the reline.",
                width=150,
                key="shell_install_rows"
            )

            install_modules_per_shell_row = st.number_input(
                "Liners per shell row",
                min_value=0,
                step=1,
                value=mill.modules_per_shell,
                help="Number of shell pieces per row.",
                width=150,
                key="install_shell_liners_per_row"
            )

            install_shell_total = install_shell_rows * install_modules_per_shell_row
            st.info(f":material/info: Shell Liners to be installed: {install_shell_total:}", width=250)
    
    with shell_cols[len(shell_cols)-1]:
        st.subheader(":material/access_time: Install time (min)")
        t_install_shell_row = st.number_input(
            "Install time (min)",
            min_value=1,
            step=5,
            value=10,
            width=150,
            key="shell_row_install_time"
        )

    return ShellInputs(
        n_rows_strip = strip_shell_rows,
        modules_per_row_strip = strip_modules_per_shell_row,
        t_row_strip = t_strip_shell_row,
        n_rows_install = install_shell_rows if not strip_install else strip_shell_rows,
        modules_per_row_install = install_modules_per_shell_row if not strip_install else strip_modules_per_shell_row,
        t_row_install = t_install_shell_row,
    )

def render_discharge(mill: Mill, strip_install: bool, n_cols: int) -> DischargeInputs:
    discharge_cols = st.columns(n_cols, border=True, width="stretch")
        
    with discharge_cols[0]:
        st.subheader(":material/construction: Stripping")
        discharge_grate_rows = st.number_input(
            "Discharge Grates",
            min_value=0,
            step=1,
            value=mill.n_discharge_grates,
            help="Count of grate segments/modules to strip and install.",
            width=150,
        )

        pulp_lifter_rows = st.number_input(
            "Pulp lifter segments",
            min_value=0,
            step=1,
            value=mill.n_pulp_lifters,
            help="Count of pulp lifter segments/modules to strip and install.",
            width=150,
        )

        st.space(size="small")
        replace_discharge_cone = st.toggle(
            "Replace discharge cone",
            value=True,
            help="Enable if the discharge cone is part of the outage scope.",
        )
    
    with discharge_cols[1]:
        st.subheader(":material/access_time: Stripping time (min)")
        t_dicharge_grate_row = st.number_input(
            "Discharge Grates",
            min_value=1,
            step=5,
            value=10,
            width=150,
        )

        t_pulp_lifter_row = st.number_input(
            "Pulp Lifters",
            min_value=1,
            step=5,
            value=10,
            width=150,
        )

        t_discharge_cone = st.number_input(
            "Discharge Cone", 
            min_value=1,
            value=4*60,
            step=30,
            width=150,
        )
    
    if not strip_install:
        with discharge_cols[2]:
            st.subheader(":material/construction: Installation")
            discharge_grate_rows_install = st.number_input(
                "Discharge Grates",
                min_value=0,
                step=1,
                value=mill.n_discharge_grates,
                help="Count of grate segments/modules to strip and install.",
                width=150,
                key="n_grates_install"
            )

            pulp_lifter_rows_install = st.number_input(
                "Pulp lifter segments",
                min_value=0,
                step=1,
                value=mill.n_pulp_lifters,
                help="Count of pulp lifter segments/modules to strip and install.",
                width=150,
                key="n_pulps_install"
            )
    
    with discharge_cols[n_cols - 1]:
        st.subheader(":material/access_time: Install time (min)")
        t_dicharge_grate_row_install = st.number_input(
            "Discharge Grates",
            min_value=1,
            step=5,
            value=10,
            width=150,
            key="t_grate_install"
        )

        t_pulp_lifter_row_install = st.number_input(
            "Pulp Lifters",
            min_value=1,
            step=5,
            value=10,
            width=150,
            key="t_pulp_install"
        )

        t_discharge_cone_install = st.number_input(
            "Discharge Cone", 
            min_value=1,
            value=4*60,
            step=30,
            width=150,
            key="t_dc_install"
        )

    return DischargeInputs(
        n_grates_strip = discharge_grate_rows,
        n_pulps_strip = pulp_lifter_rows,
        replace_dc = replace_discharge_cone,
        t_grate_strip = t_dicharge_grate_row,
        t_pulp_strip = t_pulp_lifter_row,
        t_remove_dc = t_discharge_cone if replace_discharge_cone else None,
        n_grates_install = discharge_grate_rows_install if not strip_install else discharge_grate_rows,
        n_pulps_install = pulp_lifter_rows_install if not strip_install else pulp_lifter_rows,
        t_grate_install = t_dicharge_grate_row_install,
        t_pulp_install = t_pulp_lifter_row_install,
        t_install_dc = t_discharge_cone_install if replace_discharge_cone else None,
    )

def render_mill_reline_inputs():
        
    start_date = st.date_input(
        "Project Start Date", 
        value=dt.date.today(),
        width=150
    )

    if "reline_dialog_open" not in st.session_state:
        st.session_state.reline_dialog_open = False

    if start_date and st.button(":material/tune: Reline Info"):
        st.session_state.reline_dialog_open = True
        
    # If open, render dialog
    if st.session_state.reline_dialog_open:
        render_reline_metadata_form(existing=None, template_version="2026.1")
    
    if not "reline_metadata" in st.session_state or st.session_state["reline_metadata"] is None:
        st.stop()

    meta = st.session_state["reline_metadata"]
    # this is a placeholder for eventually pulling mill info from the backend.
    # eventually pull from last reline project for that mill. 
    mill = HVC_MILLS[meta.mill_name]
    params = st.container(horizontal=True)

    t_inch = params.number_input(
                "Mill Inch time (min)",
                min_value=1,
                step=1,
                value=2,
                width=150,
                key="avg_inch_time",
                help="Average inch time (minutes)"
            )
    
    params.space("small")

    cb = params.container()

    cb.space("small")

    strip_install = cb.checkbox(
        label="Same number of Liners being stripped and installed?",
        value=True,
        help="Useful if there are more / less liners to be installed vs stripped. (Different liners being used)"
    )

    st.divider()

    n_cols = 3 if strip_install else 4 # add extra column for install segments

    tabs = st.tabs([
        ":material/input: Feed End", 
        ":material/donut_large: Shell", 
        ":material/output: Discharge End",
        ":material/calendar_month: Shift Schedule"
    ])

    with tabs[0]:
        fh_inputs = render_feed_end(
            mill=mill, strip_install=strip_install, n_cols=n_cols
        )
            
    with tabs[1]:
        shell_inputs = render_shell(
            mill=mill, strip_install=strip_install, n_cols=n_cols
        )

    with tabs[2]:
        discharge_inputs = render_discharge(
            mill=mill, strip_install=strip_install, n_cols=n_cols
        )

    with tabs[3]:
        headers = st.session_state.get("auth_headers",{})
        site_tz = None
        crews = []
        try:
            site = fetch_site(headers=headers, site_id=meta.site_id)
            site_tz = site.get("timezone", None)
        except Exception:
            pass

        try: 
            crews = get_crews(headers=headers, site_id=meta.site_id)
        except Exception:
            pass
        
        tz = render_tz_info(current_tz=site_tz)
        shift_def = render_shift_definition(project_id="change_me", current_tz=site_tz)
        edited_df = render_shift_assignment_table(crews, project_id="change_me")

    candidate = RelineScope(
        start_date=dt.datetime.combine(start_date, dt.time(hour=7,minute=0,second=0)),
        t_inch=t_inch,
        feed_end=fh_inputs,
        shell=shell_inputs,
        discharge=discharge_inputs
    )

    builder = MillRelineBuilder(mill=mill)
    st.divider()
    st.caption("Happy with your reline parameters? Build the project!")
    if st.button("Create",icon=":material/add:", type='primary'):
        with st.spinner(
            text="Building project...",
            show_time=True
        ):
            project = builder.build(inputs=candidate)
            try:
                project.site_id = meta.site_id

                if site_tz:
                    project.timezone = ZoneInfo(str(site_tz))

                shift_assigmnents = ShiftAssignment.from_df(df=edited_df, project_id=project.uuid)
                project.shift_assignments = shift_assigmnents
                
                shift_def.project_id = project.uuid # didn't have project id at original time of calling, update now.
                if site_tz:
                    shift_def.timezone = ZoneInfo(str(site_tz))
                project.timezone = shift_def.timezone
                project.shift_definition = shift_def
            except Exception as e:
                st.error(f"Error updating project schedule: {e}")
                st.stop()
            st.session_state.session.project = project
            st.success(f"Project '{project.name}' created from template.")
            st.switch_page("pages/plan.py")
            st.rerun()
