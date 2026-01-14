from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from models.project import Project
from models.phase import Phase
from models.task import Task
from models.input_models import RelineScope
import datetime as dt

class Location(Enum):
    HVC = 1
    CMM = 2

class ProjectType(Enum):
    MILL_RELINE = 1
    CRUSHER_REBUILD = 2

class MillType(Enum):
    AUTOGENOUS = 1
    SEMI_AUTOGENOUS = 2
    BALL_MILL = 3

class MillLinerType(Enum):
    MEGALINER = 1
    RUBBER = 2
    STEEL = 3


@dataclass
class Mill:
    name: str
    mill_type: MillType
    liner_type: MillLinerType

    # Feed end
    n_fh: int # number of feed head liners
    n_fh_fillers: int # number of fillers on feed end
    n_fh_grates: int # number of feed end grates

    # Shell
    n_shell: int # number of feed head shells
    modules_per_shell: int # number of shell sections in a row

    # Discharge End
    n_discharge_grates: int # number of rows of discharge grates
    n_pulp_lifters: int # number of pulp lifter rows


# -----------------------------------------
# Predefined HVC Mill Configurations
# -----------------------------------------
A_MILL = Mill(
    name="A-Mill",
    mill_type=MillType.AUTOGENOUS,
    liner_type= MillLinerType.MEGALINER,
    n_fh=24,
    n_fh_fillers=36,
    n_fh_grates=15,
    n_shell=30,
    modules_per_shell=2,
    n_discharge_grates=18,
    n_pulp_lifters=19
)

B_MILL = Mill(
    name="B-Mill",
    mill_type=MillType.AUTOGENOUS,
    liner_type=MillLinerType.MEGALINER,
    n_fh=24,
    n_fh_fillers=36,
    n_fh_grates=15,
    n_shell=30,
    modules_per_shell=2,
    n_discharge_grates=18,
    n_pulp_lifters=19
)

C_MILL = Mill(
    name="C-Mill",
    mill_type=MillType.AUTOGENOUS,
    liner_type=MillLinerType.RUBBER,
    n_fh=24,
    n_fh_fillers=36,
    n_fh_grates=15,
    n_shell=30,
    modules_per_shell=2,
    n_discharge_grates=18,
    n_pulp_lifters=19
)

D_MILL = Mill(
    name="D-Mill",
    mill_type=MillType.SEMI_AUTOGENOUS,
    liner_type=MillLinerType.STEEL,
    n_fh=24,
    n_fh_fillers=36,
    n_fh_grates=15,
    n_shell=30,
    modules_per_shell=2,
    n_discharge_grates=18,
    n_pulp_lifters=19
)

E_MILL = Mill(
    name="E-Mill",
    mill_type=MillType.SEMI_AUTOGENOUS,
    liner_type=MillLinerType.STEEL,
    n_fh=24,
    n_fh_fillers=36,
    n_fh_grates=15,
    n_shell=30,
    modules_per_shell=2,
    n_discharge_grates=18,
    n_pulp_lifters=19
)

HVC_MILLS = {
    "A-Mill": A_MILL,
    "B-Mill": B_MILL,
    "C-Mill": C_MILL,
    "D-Mill": D_MILL,
    "E-Mill": E_MILL
}
# -----------------------------------------
# Project Template and Builder Classes
#------------------------------------------

class ProjectTemplate:
    name: str = "Mill Reline"
    description: str = "A project type for mill reline projects."
    location: Location = Location.HVC
    type: ProjectType = ProjectType.MILL_RELINE
    builder: ProjectBuilder

    def __init__(self, name: str = None, description: str = None,
                 location: Location = None, type: ProjectType = None):
        if name:
            self.name = name
        if description:
            self.description = description
        if location:
            self.location = location
        if type:
            self.type = type

    def build(self) -> Project:
        pass


class ProjectBuilder:
    type: ProjectType = ProjectType.MILL_RELINE
    location: Location = Location.HVC

    def __init__(self, type: ProjectType, location: Location):
        if type:
            self.type = type
        if location:
            self.location = location

    def build(self) -> Project:
        pass


class MillRelineBuilder(ProjectBuilder):
    mill: Mill
    def __init__(self, mill: Mill):
        self.mill = mill
        super().__init__(type=ProjectType.MILL_RELINE, location=Location.HVC)

    def _build_discharge_cone_removal(self, start_date: dt.datetime) -> Phase:
        phase = Phase(
            name="Discharge Cone Removal",
        )
        end_date = start_date + dt.timedelta(hours=1)
        task1 = Task(
            name="Load Level Check",
            start_date=start_date,
            end_date=end_date
        )
        phase.add_task(task1)

        start_date = end_date
        end_date = start_date + dt.timedelta(hours=1)
        task2 = Task(
            name="Drain Mill and Clean Out",
            start_date=start_date,
            end_date=end_date
        )
        phase.add_task(task2)

        start_date = end_date
        end_date = start_date + dt.timedelta(hours=3)
        task3 = Task(
            name="Safety Talk, Tool & Work Area Setup",
            start_date=start_date,
            end_date=end_date
        )
        phase.add_task(task3)
        return phase

    def _build_stripping_fh(self, inputs: RelineScope, start_dt: dt.datetime) -> Phase:
        phase = Phase(
            name="Stripping FH & Shell"
        )
        remaining_fh = inputs.feed_head_fillers
        #fh_sequence = (remaining_fh - 3 * i for i in range(remaining_fh, start=1))

        remaining_filler = inputs.feed_head_fillers
        #filler_sequence = (remaining_fh - 3 * i for i in range(remaining_filler, start = 1))

        # find last element of each naive sequence S.T. it is divisible by two. 
        num_fh = 3
        num_filler = 3
        num_shell_row = 2
        task_start = start_dt

        prev_task = None

        for i in range(inputs.shell_rows):
            # ---------------------------------
            # Stripping Task
            # ---------------------------------
            duration = 2 * inputs.t_shell_row * num_shell_row + num_fh * inputs.t_fh + num_filler * inputs.t_fh_filler
            task_end = task_start + dt.timedelta(minutes=duration)
            predecessor_id = prev_task.uuid if prev_task else None

            task = Task(
                name=f"Remove 2 Rows Shell ({2 * inputs.modules_per_shell_row}) {num_fh} FH & {num_filler} Filler",
                start_date=task_start,
                end_date=task_end,
                predecessor_ids=[predecessor_id] if prev_task else []
            )
            
            phase.add_task(task)
            prev_task = task

            #---------------------------------
            # Inching
            #---------------------------------
            task_start = task_end
            task_end = task_start + dt.timedelta(minutes=inputs.t_inch)

            predecessor_id = prev_task.uuid if prev_task else None
            
            task = Task(
                name=f"Inch {i+1}",
                start_date=task_start,
                end_date=task_end,
                predecessor_ids=[predecessor_id] if prev_task else []
            )
            phase.add_task(task)

            prev_task = task
        
        return phase


    def build(self, inputs: RelineScope) -> Project:
        project = Project(
            name=f"{self.mill.name} Reline Project: {inputs.start_date.strftime('%B %Y')}",
            description=f"Mill reline project for {self.mill.name} starting on {inputs.start_date.strftime('%B %Y')}.\n Auto-generated by GanttBuddy.",
        )

        # Build phases and tasks based on inputs

        # ------------------------------------------
        # Phase 1: Discharge Cone Removal
        # ------------------------------------------        
        project.add_phase(
            self._build_discharge_cone_removal(
                start_date=dt.datetime.combine(inputs.start_date, dt.time(hour=7))
            )
        )

        phase_end = project.end_date

        # ------------------------------------------
        # Phase 2: Stripping FH & Shell
        # ------------------------------------------
        project.add_phase(
            self._build_stripping_fh(
                inputs=inputs,
                start_dt=phase_end,
            )
        )

        phase_end = project.end_date

        return project