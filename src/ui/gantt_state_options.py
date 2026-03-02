import streamlit as st

from models.delay import DelayEditorRow, DelayType
from models.gantt_state import GanttState
from logic.gantt_builder import _normalize_delay_type

def render_gantt_options(state: GanttState, delay_rows: list[DelayEditorRow]):
    st.subheader("Gantt Chart Options")
    c1, c2 = st.columns(2,border=True)
    with c1:
        st.caption("Planned Task Appearance")
        state.show_planned = st.toggle(
            label="Show Planned",
            value=state.show_planned,
            key="gantt_option_show_planned"
        )

        state.planned_color = st.color_picker(
            label="Planned Color",
            value=state.planned_color,
            key="gantt_option_planned_color"
        )

    with c2:
        st.caption("Actual Task Appearance")
        st.write("")
        state.show_actual = st.toggle(
            label="Show Actuals",
            value=state.show_actual,
            key="gantt_option_show_actual"
        )

        state.actual_color = st.color_picker(
            label="Actual Task Color",
            value=state.actual_color,
            key="gantt_option_actual_color"
        )

    state.show_delay_windows = st.checkbox(
        label="Show registered delays",
        value=state.show_delay_windows,
        key="gantt_option_show_delay_windows",
    )
    all_types = sorted({_normalize_delay_type(r.delay_type) for r in delay_rows})
    selected_delay_types = all_types
    if state.show_delay_windows:
        selected_delay_types = st.multiselect(
            "Delay types",
            options=all_types,
            default=all_types,
            key="gantt_overlay_delay_types",
        )
        

    state.shade_non_working_time = st.checkbox(
        label="Shade Non-Working Time",
        value=state.shade_non_working_time,
        key="gantt_option_shade_non_working_time"
    )

    specify_x_axis = st.toggle(
        label="Specify X-Axis Range",
        value=state.x_axis_start is not None and state.x_axis_end is not None,
        key="gantt_option_specify_x_axis"
    )

    if specify_x_axis:
        c1, c2 = st.columns(2)
        with c1:
            state.x_axis_start = st.datetime_input(
                label="X-Axis Start",
                value=state.x_axis_start if state.x_axis_start else None,
                key="gantt_option_x_axis_start"
            )
        with c2:
            state.x_axis_end = st.datetime_input(
                label="X-Axis End",
                value=state.x_axis_end if state.x_axis_end else None,
                key="gantt_option_x_axis_end"
            )
    else:
        state.x_axis_start = None
        state.x_axis_end = None
       

