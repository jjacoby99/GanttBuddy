from dataclasses import dataclass, field
from typing import Literal


@dataclass
class PlanState:
    project_id: str = ""
    _expanded_phase_ids: set[str] = field(default_factory=set)
    show_actuals: bool = False
    highlight_delayed_tasks: bool = False
    view_mode: Literal["Simple", "Detailed"] = "Detailed"

    def sync_with_project(self, project_id: str, phase_ids: list[str]) -> None:
        phase_id_set = set(phase_ids)

        # A project switch should always rebuild the expander map from the new phase ids.
        if self.project_id != project_id:
            self.project_id = project_id
            self._expanded_phase_ids = set()
            return

        self._expanded_phase_ids.intersection_update(phase_id_set)

    def add_phase(self, phase_id: str) -> None:
        self._expanded_phase_ids.discard(phase_id)

    def remove_phase(self, phase_id: str) -> None:
        self._expanded_phase_ids.discard(phase_id)

    def is_phase_expanded(self, phase_id: str) -> bool:
        return phase_id in self._expanded_phase_ids

    def expanded_phase_ids(self) -> set[str]:
        return set(self._expanded_phase_ids)

    def toggle_phase_expansion(self, pid: str):
        if pid in self._expanded_phase_ids:
            self._expanded_phase_ids.remove(pid)
            return
        self._expanded_phase_ids.add(pid)

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
