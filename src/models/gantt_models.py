from dataclasses import dataclass, field

@dataclass(frozen=True)
class GanttInputs:
    show_actuals: bool = False
    use_bta_colors: bool = True
    shade_non_working: bool = True