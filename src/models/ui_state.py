from __future__ import annotations
from dataclasses import dataclass
import streamlit as st

@dataclass
class UIState:
    show_settings: bool = False
    show_add_phase: bool = False
    show_edit_phase: bool = False
    show_add_task: bool = False
    show_edit_task: bool = False
    analysis_phase_index: int = 0

    execution_phase_index: int = 0
    execution_task_index: int = 0 # task index within the execution phase
    show_edit_project: bool = False

    #selected_phase_id: str | None = None  # for context when adding tasks

    def set_execution_phase_index(self, value: int):
        if value < 0:
            value = 0
        self.execution_phase_index = value
        self.execution_task_index = 0  # reset task index when phase changes
