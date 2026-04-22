from __future__ import annotations

from pydantic import BaseModel


class ProjectDeleteImpact(BaseModel):
    project_id: str
    project_name: str
    organization_id: str
    phases_count: int = 0
    tasks_count: int = 0
    phase_predecessor_links_count: int = 0
    task_predecessor_links_count: int = 0
    events_count: int = 0
    project_members_count: int = 0
    project_settings_count: int = 0
    project_metadata_count: int = 0
    shift_definitions_count: int = 0
    shift_assignments_count: int = 0
    delays_count: int = 0
    data_sources_count: int = 0
    signal_definitions_count: int = 0
    ingestion_runs_count: int = 0
    signal_observations_count: int = 0
    todos_count: int = 0
    todos_direct_count: int = 0
    todos_task_linked_count: int = 0
