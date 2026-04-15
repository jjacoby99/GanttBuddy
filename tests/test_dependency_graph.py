from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from models.constraint import Constraint, ConstraintRelation
from models.phase import Phase
from models.project import Project
from models.task import Task
from ui.dependency_graph import build_dependency_graph_data


def test_dependency_graph_includes_task_and_phase_edges() -> None:
    phase_a = Phase(name="Phase A")
    task_a = Task(
        name="Task A",
        start_date=datetime(2026, 4, 1, 7, 0),
        end_date=datetime(2026, 4, 1, 9, 0),
    )
    phase_a.add_task(task_a)

    phase_b = Phase(
        name="Phase B",
        constraints=[
            Constraint(
                predecessor_id=phase_a.uuid,
                predecessor_kind="phase",
                relation_type=ConstraintRelation.FS,
                lag=timedelta(hours=4),
            )
        ],
    )
    task_b = Task(
        name="Task B",
        start_date=datetime(2026, 4, 1, 10, 0),
        end_date=datetime(2026, 4, 1, 12, 0),
        constraints=[
            Constraint(
                predecessor_id=task_a.uuid,
                predecessor_kind="task",
                relation_type=ConstraintRelation.SS,
                lag=timedelta(hours=2),
            )
        ],
    )
    phase_b.add_task(task_b)

    project = Project(name="Dependency Test")
    project.add_phase(phase_a)
    project.add_phase(phase_b)

    graph = build_dependency_graph_data(project)

    assert len(graph.bubbles) == 2
    assert {node.kind for node in graph.nodes} == {"phase", "task"}
    assert len(graph.edges) == 2
    assert any(edge.target_id == task_b.uuid and edge.label == "SS (2h)" for edge in graph.edges)
    assert any(edge.target_id == phase_b.uuid and edge.label == "FS (4h)" for edge in graph.edges)


def test_dependency_graph_bubble_tracks_task_count() -> None:
    phase = Phase(name="Execution")
    for idx in range(3):
        phase.add_task(
            Task(
                name=f"Task {idx + 1}",
                start_date=datetime(2026, 4, 1, 7 + idx, 0),
                end_date=datetime(2026, 4, 1, 8 + idx, 0),
            )
        )

    project = Project(name="Bubble Test")
    project.add_phase(phase)

    graph = build_dependency_graph_data(project)
    bubble = graph.bubbles[0]

    assert bubble.y1 > bubble.y0
    assert bubble.y0 <= -4.0
    assert [node.label for node in graph.nodes if node.kind == "task"] == ["Task 1", "Task 2", "Task 3"]
