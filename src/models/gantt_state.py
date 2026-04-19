from dataclasses import dataclass, field
import datetime as dt

@dataclass
class GanttState:
    phase_idx: int = 0
    show_actual: bool = False
    show_planned: bool = True
    bta_colors: bool = True
    shade_non_working_time: bool = True

    show_delay_windows: bool = False
    selected_delay_types: list[str] = field(default_factory=list)
    x_axis_start: dt.datetime = None
    x_axis_end: dt.datetime = None

    actual_color: str = "#F4B084"
    planned_color: str = "#2A9E77"