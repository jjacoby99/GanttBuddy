from dataclasses import dataclass, field
from typing import Literal


@dataclass
class PlanState:
    project_id: str = ""
    expanded_phases: dict[str, bool] = field(default_factory=dict)
    show_actuals: bool = False
    highlight_delayed_tasks: bool = False
    initialized: bool = False
    view_mode: Literal["Simple", "Detailed"] = "Detailed"

    def initialize_expanded_phases(self, phase_ids: list[str]):
        if self.initialized:
            return
        if len(self.expanded_phases) != len(phase_ids):
            for pid in phase_ids:
                self.expanded_phases.setdefault(pid, False)
            
            # clear potential old keys
            for key in list(self.expanded_phases.keys()):
                if key not in phase_ids:
                    del self.expanded_phases[key]

        self.initialized = True

    def add_phase(self, phase_id: str) -> None:
        self.expanded_phases[phase_id] = False

    def remove_phase(self, phase_id: str) -> None:
        if phase_id in self.expanded_phases:
            del self.expanded_phases[phase_id]

    def toggle_phase_expansion(self, pid: str):
        if pid not in self.expanded_phases:
            return
        self.expanded_phases[pid] = not self.expanded_phases[pid]

    def toggle_view_mode(self):
        self.view_mode = "Detailed" if self.view_mode == "Simple" else "Simple"


class TaskColumns:
    name: int = 0
    planned_start: int = 1
    planned_finish: int = 2
    status: int = 3
    actual_start: int | None = None
    actual_finish: int | None = None
    edit: int = 4

    show_actuals: bool = False

    def __init__(self, show_actuals: bool=False):
        self.show_actuals = show_actuals

        self.name = 0
        self.planned_start = 1
        self.planned_finish = 2
        self.status = 3
        self.edit = 4
        if show_actuals:
            self.actual_start = 4
            self.actual_finish = 5
            self.edit = 6

    def get_col_widths(self) -> list[int]:
        if self.show_actuals:
            return [5, 2, 2, 2, 2, 2, 1]

        return [5,2,2,2,1]