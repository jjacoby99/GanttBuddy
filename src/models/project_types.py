from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from models.project import Project
from models.phase import Phase
from models.task import Task
from models.input_models import RelineScope
import datetime as dt
from itertools import cycle, islice

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
    n_pulp_lifters=17
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

        for i in range(inputs.shell_rows // 2):
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

            # do not inch on the last row of shell
            if i == inputs.shell_rows / 2 - 1:
                continue
            
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
            task_start = task_end
        
        return phase

    def _build_install_fh_shell(self, inputs: RelineScope, start_dt: dt.datetime) -> Phase:
        phase = Phase(
            name="Install FH & Shell"
        )

        num_shell_row = 2
        num_head = 2
        num_grate = 1

        task_start = start_dt

        prev_task = None
        
        for i in range(inputs.shell_rows // 2):
            # ---------------------------------
            # Stripping Task
            # ---------------------------------
            duration = inputs.t_shell_row * num_shell_row + num_head * inputs.t_fh + num_grate * inputs.feed_head_grates
            task_end = task_start + dt.timedelta(minutes=duration)
            predecessor_id = prev_task.uuid if prev_task else None

            task = Task(
                name=f"Install {num_shell_row} rows Megaliner Shell, {num_head} Megaliner Head, {num_grate} Grate",
                start_date=task_start,
                end_date=task_end,
                predecessor_ids=[predecessor_id] if prev_task else []
            )
            
            phase.add_task(task)
            prev_task = task

            #---------------------------------
            # Inching
            #---------------------------------

            # do not inch on the last row of shell
            if i == inputs.shell_rows / 2 - 1:
                continue
            
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
            task_start = task_end
        
        return phase

    def _build_strip_discharge_grates_pulps_fillers(self, inputs: RelineScope, start_dt: dt.datetime) -> Phase:
        phase = Phase(
            name=f"Strip Discharge Grates, Pulp Lifters, & Fillers"
        )

        first_task: str = "Strip 1 Row of Grates/Interlock"
        work_sequence = [
            "Strip 1 Row of Grates/Interlock & Throat Plate  + Inner, Middle, and Outer Pulp",
            "Strip 1 Row of Grates/Interlock + Middle & Outer Pulp",
        ]

        num_iterations = inputs.discharge_grate_rows - 1
        it = islice(cycle(work_sequence), num_iterations)

        first_duration = 2.67

        task_start = start_dt
        task_end = start_dt + dt.timedelta(hours=first_duration)

        task = Task(
            name=f"Strip 1 Row of Grates/Interlock",
            start_date=task_start,
            end_date=task_end,
            predecessor_ids=[]
        )

        phase.add_task(task)

        inch_end = task_end + dt.timedelta(minutes=inputs.t_inch)

        inch = Task(
            name="Inch 1",
            start_date = task_end,
            end_date=inch_end,
            predecessor_ids=[task.uuid]
        )
        phase.add_task(inch)
        prev_task = inch
        task_start = inch_end
        for i, work_task in enumerate(it):
            # ---------------------------------
            # Stripping Task
            # ---------------------------------
            
            duration = inputs.t_discharge_grate_row + inputs.t_pulp_lifter_row
            
            # account for interlock 
            duration += 30 if work_task != "Strip 1 Row of Grates/Interlock + Middle & Outer Pulp" else 0

            task_end = task_start + dt.timedelta(minutes=duration)
            predecessor_id = prev_task.uuid if prev_task else None

            task = Task(
                name=work_task,
                start_date=task_start,
                end_date=task_end,
                predecessor_ids=[predecessor_id] if prev_task else []
            )
            
            phase.add_task(task)
            prev_task = task

            #---------------------------------
            # Inching
            #---------------------------------

            # do not inch on the last row of shell
            if i == inputs.shell_rows - 2:
                continue
            
            task_start = task_end
            task_end = task_start + dt.timedelta(minutes=inputs.t_inch)

            predecessor_id = prev_task.uuid if prev_task else None
            
            task = Task(
                name=f"Inch {i+2}",
                start_date=task_start,
                end_date=task_end,
                predecessor_ids=[predecessor_id] if prev_task else []
            )

            phase.add_task(task)

            prev_task = task
            task_start = task_end
        
        return phase

    def _build_install_pulp_lifters(self, inputs: RelineScope, start_dt: dt.datetime) -> Phase:
        phase = Phase(
            name="Install Pulp lifters"
        )

        task_start = start_dt
        prev_task = None
        for i in range(inputs.pulp_lifter_rows):
            duration = inputs.t_pulp_lifter_row
            task_end = task_start + dt.timedelta(minutes=duration)

            task = Task(
                name="Install 1 rows pulp lifters",
                start_date=task_start,
                end_date=task_end,
                predecessor_ids=[prev_task.uuid] if prev_task else []
            )
            phase.add_task(task)

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
            task_start = task_end

        return phase

    def _build_install_de_grates_fillers(self, inputs: RelineScope, start_dt: dt.datetime) -> Phase:
        phase = Phase(
            name="Install Discharge Grates & Fillers"
        )

        task_start = start_dt
        prev_task = None

        for i in range(inputs.discharge_grate_rows):
            duration = inputs.t_discharge_grate_row
            task_end = task_start + dt.timedelta(minutes=duration)

            task = Task(
                name="Install Discharger - 1 Inner, Mid and Outer, Filling Segment + add washout repairs",
                start_date=task_start,
                end_date=task_end,
                predecessor_ids=[prev_task.uuid] if prev_task else []
            )

            phase.add_task(task)

            task_start = task_end
            duration = inputs.t_inch
            task_end = task_start + dt.timedelta(minutes=duration)
            
            inch = Task(
                name=f"Inch {i+1}",
                start_date=task_start,
                end_date=task_end,
                predecessor_ids=[task.uuid]
            ) 
            phase.add_task(inch)
            task_start = task_end
            prev_task = inch
        return phase


    def _build_install_discharge_cone(self, t_discharge: int, start_dt: dt.datetime) -> Phase:
        phase = Phase(
            name="Milestone - Install Discharge Cone"
        )

        task = Task(
            name="Install Discharge Cone",
            start_date=start_dt,
            end_date=start_dt + dt.timedelta(minutes=t_discharge)
        )
        phase.add_task(task)
        return phase

    def _build_torque_check(self, start_dt: dt.datetime) -> Phase:
        phase = Phase(
            name="Torque Check"
        )
        end_date = start_dt + dt.timedelta(minutes=5*60)
        t1 = Task(
            name="Torque Check on Shell, Feed & Discharge",
            start_date=start_dt,
            end_date=end_date
        )
        phase.add_task(t1)

        start_date = end_date
        end_date = start_date + dt.timedelta(minutes=30)
        t2 = Task(
            name="Liner Handler Removal",
            start_date=start_date,
            end_date=end_date
        )
        phase.add_task(t2)

        start_date = end_date
        end_date = start_date + dt.timedelta(minutes=60)
        t3 = Task(
            name="Housekeeping",
            start_date=start_date,
            end_date=end_date
        )
        phase.add_task(t3)

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

        # ------------------------------------------
        # Phase 3: Stripping FH & Shell
        # ------------------------------------------
        project.add_phase(
            self._build_install_fh_shell(
                inputs=inputs,
                start_dt=phase_end
            )
        )

        phase_end = project.end_date


        # ------------------------------------------
        # Phase 4: Strip Discharge Grates, Pulp Lifters, & Fillers
        # ------------------------------------------
        project.add_phase(
            self._build_strip_discharge_grates_pulps_fillers(
                inputs=inputs,
                start_dt=phase_end
            )
        )

        phase_end = project.end_date


        # ------------------------------------------
        # Phase 5: Install Pulp Lifters
        # ------------------------------------------
        project.add_phase(
            self._build_install_pulp_lifters(
                inputs=inputs,
                start_dt=phase_end
            )
        )

        phase_end = project.end_date

        # ------------------------------------------
        # Phase 6: Install Discharge Grates & Fillers
        # ------------------------------------------
        project.add_phase(
            self._build_install_de_grates_fillers(
                inputs=inputs,
                start_dt=phase_end
            )
        )

        phase_end = project.end_date

        # ------------------------------------------
        # Phase 7: Install Discharge Cone
        # ------------------------------------------
        t_discharge = inputs.t_discharge_cone
        if inputs.replace_discharge_cone:
            project.add_phase(
                self._build_install_discharge_cone(
                    start_dt=phase_end,
                    t_discharge=t_discharge
                )
            )
            phase_end = project.end_date

        # ------------------------------------------
        # Phase 8: Torque Check
        # ------------------------------------------
        project.add_phase(
            self._build_torque_check(phase_end)
        )
        
        project.settings.work_all_day = True
        project.settings.set_all_working_days()
        return project