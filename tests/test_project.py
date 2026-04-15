from __future__ import annotations

import pytest
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from models.constraint import Constraint, ConstraintRelation
from models.project import Project
from models.task import Task
from models.phase import Phase

@pytest.fixture
def simple_project() -> Project:
    """
        Provides a simple project with 1 phase containing 2 tasks: t1 and t2.

        Notes
            - t2 has t1 as a predecessor.
    """
    t1 = Task(
        name="Task 1",
        start_date=datetime(year=2025,month=11,day=24,hour=7,minute=0,second=0),
        end_date=datetime(year=2025,month=11,day=25,hour=17,minute=0,second=0),
    )

    t2 = Task(
        name="Task 2",
        start_date=datetime(year=2025,month=11,day=25,hour=17,minute=0,second=0),
        end_date=datetime(year=2025,month=11,day=27,hour=17,minute=0,second=0),
        constraints=[
            Constraint(
                predecessor_id=t1.uuid,
                predecessor_kind="task",
                relation_type=ConstraintRelation.FS,
            )
        ],
    )

    phase = Phase(
        name="Phase 1",
    )

    phase.add_task(t1)
    phase.add_task(t2)

    proj = Project(
        name="Simple Project"
    )

    proj.add_phase(phase)
    return proj



def test_update_task_cascades(simple_project: Project):
    """
        Verifies that updating a task within a project that has other tasks with it as predecessors
        has the side effect of changing the successor's start / end dates.

        Example:
            Task A: 2025/11/24 7:00 -> 2025/11/25 17:00
            Task B: 2025/11/25 17:00 -> 2025/11/27 17:00
                - Has Task A as a predecessor
            Task C: 2025/11/27 17:00 -> 2025/11/28 17:00
                - No predecessors
            

            Changing Task A's start date to 2025/11/25 10:00 (delayed by 3 hrs) should have the effect of 
            shifting Task A's end date by 3 hours, but also should delay Task B's start and end by the 
            same 3 hrs. 

            Since Task C doesn't have Task A or B as a predecessor, its start & end dates should not be 
            effected by this shift.

        Note that this method intentionally doesn't test the actual start and end: just the planned.
        The actual start and end are assumed to be accurate records that are not to be touched.
    """

    proj = simple_project
    delay_hrs = 3

    tid1 = (proj.phases[proj.phase_order[0]]).task_order[0]
    tid2 = (proj.phases[proj.phase_order[0]]).task_order[1]
    
    old_t1 = (proj.phases[proj.phase_order[0]]).tasks[tid1]
    old_t2 = (proj.phases[proj.phase_order[0]]).tasks[tid2]

    # New task's start and end delayed by 3 hrs
    new_t1 = Task(
        name="Task 1",
        start_date=old_t1.start_date + timedelta(hours=delay_hrs),
        end_date=old_t1.end_date + timedelta(hours=delay_hrs)
    )

    t1_old_start = old_t1.start_date
    t1_old_end = old_t1.end_date

    t2_old_start = old_t2.start_date
    t2_old_end = old_t2.end_date

    proj.update_task(
        phase=proj.phases[proj.phase_order[0]],
        old_task=old_t1,
        new_task=new_t1
    )

    new_t1_in_proj: Task = (proj.phases[proj.phase_order[0]]).tasks[tid1]
    new_t2_in_proj: Task = (proj.phases[proj.phase_order[0]]).tasks[tid2]


    # ensure T1's start and end dates have been updated
    assert new_t1_in_proj.start_date == t1_old_start + timedelta(hours=delay_hrs), "Task 1's new start date wasn't delayed by 3 hrs"
    assert new_t1_in_proj.end_date == t1_old_end + timedelta(hours=delay_hrs), "Task 1's new end date wasn't delayed by 3 hrs"

    # ensure T2's start and end dates have been updated
    assert new_t2_in_proj.start_date == t2_old_start + timedelta(hours=delay_hrs), "Task 2's new start date wasn't delayed by 3 hrs"
    assert new_t2_in_proj.end_date == t2_old_end + timedelta(hours=delay_hrs), "Task 2's new end date wasn't delayed by 3 hrs"


def test_task_constraints_preserve_explicit_constraint_definitions() -> None:
    task = Task(
        name="Task B",
        start_date=datetime(2025, 11, 25, 17, 0),
        end_date=datetime(2025, 11, 27, 17, 0),
        constraints=[
            Constraint(
                predecessor_id="task-a",
                predecessor_kind="task",
                relation_type=ConstraintRelation.FS,
            ),
            Constraint(
                predecessor_id="task-c",
                predecessor_kind="task",
                relation_type=ConstraintRelation.FF,
            ),
        ],
    )

    assert len(task.constraints) == 2
    assert all(constraint.predecessor_kind == "task" for constraint in task.constraints)
    assert task.constraints[0].predecessor_id == "task-a"
    assert task.constraints[0].relation_type == ConstraintRelation.FS
    assert task.constraints[1].predecessor_id == "task-c"
    assert task.constraints[1].relation_type == ConstraintRelation.FF


def test_delete_task_removes_constraints_from_successors(simple_project: Project) -> None:
    proj = simple_project
    phase = proj.phases[proj.phase_order[0]]
    task_a = phase.tasks[phase.task_order[0]]
    task_b = phase.tasks[phase.task_order[1]]

    removed = phase.delete_task(task_a)

    assert removed == 1
    assert task_b.constraints == []


def test_multiple_constraints_resolve_successor_to_latest_required_start() -> None:
    phase = Phase(name="Phase 1")
    task_a = Task(
        name="Task A",
        start_date=datetime(2026, 2, 1, 7, 0),
        end_date=datetime(2026, 2, 1, 9, 0),
    )
    task_b = Task(
        name="Task B",
        start_date=datetime(2026, 2, 1, 8, 0),
        end_date=datetime(2026, 2, 1, 12, 0),
    )
    task_c = Task(
        name="Task C",
        start_date=datetime(2026, 2, 1, 9, 0),
        end_date=datetime(2026, 2, 1, 11, 0),
        constraints=[
            Constraint(predecessor_id=task_a.uuid, predecessor_kind="task", relation_type=ConstraintRelation.FS),
            Constraint(
                predecessor_id=task_b.uuid,
                predecessor_kind="task",
                relation_type=ConstraintRelation.SS,
                lag=timedelta(hours=2),
            ),
        ],
    )

    phase.add_task(task_a)
    phase.add_task(task_b)
    phase.add_task(task_c)

    phase.resolve_schedule()

    assert task_c.start_date == datetime(2026, 2, 1, 10, 0)
    assert task_c.end_date == datetime(2026, 2, 1, 12, 0)

    
