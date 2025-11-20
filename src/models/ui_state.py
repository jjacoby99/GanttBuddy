from dataclasses import dataclass
import streamlit as st

@dataclass
class UIState:
    show_settings: bool = False
    show_add_phase: bool = False
    show_edit_phase: bool = False
    show_add_task: bool = False
    show_edit_task: bool = False
    #selected_phase_id: str | None = None  # for context when adding tasks
