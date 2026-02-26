import json
import os
import pandas as pd
from models.project import Project
from models.phase import Phase
from models.project_settings import ProjectSettings
from models.project_metadata import RelineMetadata
from models.project_type import ProjectType

from models.shift_schedule import ShiftDefinition, ShiftAssignment

from models.task import Task, TaskType
from pprint import pprint
import math
from dataclasses import dataclass, field
from typing import Any, Optional
import re
from openpyxl import Workbook, load_workbook
from io import BytesIO
from typing import Union
import datetime as dt


@dataclass
class DataColumn:
    name: str
    column: int


@dataclass
class ExcelParameters:
    sheet_name: str = "Daily Schedule"

    columns: list[DataColumn] = field(default_factory=list[DataColumn])

    project_name_cell: str = "A5"
    start_row: int = 8

    def get_pd_usecols(self):
        return [col.column - 1 for col in self.columns]
    
    def get_col_names(self):
        return [col.name for col in self.columns]
    
    def get_df_index(self, col_name: str) -> int:
        for i, col in enumerate(self.columns):
            if col.name == col_name:
                return i
        raise KeyError(f"Column name '{col_name}' not found in columns.")
    
    def __getitem__(self, key: Union[int, str]) -> DataColumn:
        if isinstance(key, int):
            if key < len(self.columns):
                return self.columns[key]
            raise IndexError(f"Index {key} out of range for columns of length {len(self.columns)}.")
        elif isinstance(key, str):
            for col in self.columns:
                if col.name == key:
                    return col.column
        raise KeyError(f"Column name '{key}' not found in columns.")
    

class ProjectLoader():
    @staticmethod
    def load_json_file(file_path: str) -> dict:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File '{file_path}' not found.")
        if not os.path.splitext(file_path)[1].lower() == ".json":
            raise ValueError(f"File '{file_path}' is not a .json file.")
        
        with open(file_path, "r") as f:
            proj_dict = json.load(f)
        
        return proj_dict

    @staticmethod
    def load_project(proj_dict: dict) -> Project:
        for key in ["name", "phases", "settings"]:
            if not key in proj_dict:
                raise ValueError(f"Key '{key}' not found in project dictionary.")
            
        project = Project(name=proj_dict["name"], description=proj_dict.get("description", ""))
        
        phases = [Phase.from_dict(phase_dict) for phase_dict in proj_dict["phases"]]
        
        if len(phases) > 1:
            for i, phase in enumerate(phases[1:]):
                if phase.preceding_phase:
                    pass

        project.settings = ProjectSettings.from_dict(proj_dict["settings"])

        return project

import warnings
warnings.filterwarnings(
    "ignore",
    message=".*extension is not supported and will be removed",
    module="openpyxl\\worksheet\\_reader"
)   

class ExcelProjectLoader():

    _phase_pat = re.compile(r"\b(\d+(?:\.\d+)?)\s*day(s)?\b", re.IGNORECASE)
    _hours_pat = re.compile(r"\b(\d+(?:\.\d+)?)\s*hour(s)?\b", re.IGNORECASE)

    @staticmethod
    def _is_nan(x: Any) -> bool:
        return x is None or (isinstance(x, float) and math.isnan(x)) or (isinstance(x, pd._libs.missing.NAType))
    
    @staticmethod
    def _coerce_str(x: Any) -> str:
        if ExcelProjectLoader._is_nan(x):
            return ""
        return str(x).strip()
    
    @staticmethod
    def _coerce_bool(x: Any) -> bool:
        """
        Coerce a pandas-read Excel cell value to a strict Python bool.

        Rules:
        - NaN/blank -> True (matches your default behavior)
        - bool -> itself
        - ints/floats -> 0 is False, non-zero is True
        - strings -> accepts common true/false tokens (case/whitespace-insensitive)
        True tokens:  "true", "t", "yes", "y", "1", "on"
        False tokens: "false", "f", "no", "n", "0", "off"
        - anything else -> ValueError (fail fast so bad Excel data doesn't silently pass)
        """
        if ExcelProjectLoader._is_nan(x):
            return True

        # Already a Python bool (note: bool is a subclass of int, so do this before int checks)
        if isinstance(x, bool):
            return x

        # Numeric (covers numpy numeric types too)
        if isinstance(x, (int, float)):
            # handle weird floats like 0.0, 1.0
            return bool(int(x))

        # Strings (common when Excel column has mixed types or user-entered text)
        if isinstance(x, str):
            s = x.strip().lower()
            if s == "":
                return True  # treat empty cell as default True
            if s in {"true", "t", "yes", "y", "1", "on"}:
                return True
            if s in {"false", "f", "no", "n", "0", "off"}:
                return False
            raise ValueError(f"Invalid boolean string: {x!r}")

        # Pandas sometimes gives Timestamp/other objects if the column is messed up
        raise ValueError(f"Cannot coerce to bool from type={type(x).__name__}, value={x!r}")

    @staticmethod
    def is_phase_cell(cell: Any) -> bool:
        """
        A row is a phase if PLANNED DURATION looks like a 'Days' string, not a plain number.
        """
        if ExcelProjectLoader._is_nan(cell):
            return False
        if isinstance(cell, (int, float)) and not isinstance(cell, bool):
            return False  # plain numeric => task
        s = ExcelProjectLoader._coerce_str(cell)
        if not s:
            return False
        # If it mentions 'day'/'days' anywhere, treat as phase.
        return bool(ExcelProjectLoader._phase_pat.search(s))
    
    @staticmethod
    def parse_duration_hours(cell: Any) -> Optional[float]:
        """
        - If numeric -> hours directly
        - If string like '3 Days (72 Hours)' -> prefer Days*24; else use Hours if present; else None
        """
        if ExcelProjectLoader._is_nan(cell):
            return None
        if isinstance(cell, (int, float)) and not isinstance(cell, bool):
            return float(cell)

        s = ExcelProjectLoader._coerce_str(cell)
        if not s:
            return None

        m_days = ExcelProjectLoader._phase_pat.search(s)
        if m_days:
            days = float(m_days.group(1))
            return days * 24.0

        m_hours = ExcelProjectLoader._hours_pat.search(s)
        if m_hours:
            return float(m_hours.group(1))

        # fallback: try to parse a bare number from string (sometimes cells are "  8  ")
        try:
            return float(s)
        except ValueError:
            return None

    @staticmethod
    def _infer_task_type(task_str: str) -> TaskType:
        check = task_str.lower()
        if "inch" in check:
            return TaskType.INCH
        
        if "strip" in check or "remove" in check:
            return TaskType.STRIP
        
        if "install" in check:
            return TaskType.INSTALL
        
        return TaskType.GENERIC

    def _infer_columns(wb: Workbook, params: ExcelParameters):
        """
            Reads the header row of the provided Workbook
            Infers data columns present
        """

        ws = wb[params.sheet_name]

    
    @staticmethod
    def load_excel_project(file, params: ExcelParameters) -> tuple[Project, Optional[RelineMetadata]]:
        if file is None:
            raise ValueError("No file provided.")
        
        data = file.read()

        bio_pd = BytesIO(data)
        bio_opx = BytesIO(data)

        df = pd.read_excel(
            bio_pd,
            sheet_name=params.sheet_name,
            header=params.start_row - 2,
            usecols=params.get_pd_usecols(),
        )

        df.columns = params.get_col_names()
        df = df.drop(0) # remove header row
        
        df['NOTES'] = df['NOTES'].fillna("") # fill notes NaN with empty string
        df['ACTUAL START'] = df['ACTUAL START'].replace({pd.NaT: None})
        df['ACTUAL END'] = df['ACTUAL END'].replace({pd.NaT: None})

        # Drop fully empty rows based on ACTIVITY being blank
        df["ACTIVITY"] = df["ACTIVITY"].astype(str).str.strip()
        df = df[df["ACTIVITY"] != ""].reset_index(drop=True)
        
        wb = load_workbook(bio_opx, read_only=True, data_only=True)
        plan_sheet = wb[params.sheet_name]
        proj_name = plan_sheet[params.project_name_cell].value

        project = Project(name=proj_name if proj_name else "Untitled Project")

        project_id = ExcelProjectLoader.load_project_id(wb)
        print(f"Loaded project_id {project_id}. Type: {type(project_id)}")
        if project_id is not None:
            project.uuid = project_id #existing project, preserve uuid for backend.

        project.shift_definition = ExcelProjectLoader.load_shift_definition(file, project_id=project.uuid)
        project.shift_assignments = ExcelProjectLoader.load_shift_assignments(file, project_id=project.uuid)
        proj_type = ExcelProjectLoader.load_project_type(wb)
        project.project_type = proj_type
        metadata = None
        if proj_type == ProjectType.MILL_RELINE:
            metadata = ExcelProjectLoader.load_metadata(wb)
        current_phase = None
        unassigned_phase = None

        def mk_task(row)-> Task:
            uuid = ExcelProjectLoader._coerce_str(row["UUID"])
            if uuid == "":
                from models.task import new_id
                uuid = new_id()
            name = ExcelProjectLoader._coerce_str(row["ACTIVITY"])
            return Task(
                name=name,
                start_date=pd.to_datetime(row["PLANNED START"], errors="coerce").to_pydatetime().astimezone() if not ExcelProjectLoader._is_nan(row["PLANNED START"]) else None,
                end_date=pd.to_datetime(row["PLANNED END"], errors="coerce").to_pydatetime().astimezone() if not ExcelProjectLoader._is_nan(row["PLANNED END"]) else None,
                actual_end=pd.to_datetime(row["ACTUAL END"], errors="coerce").to_pydatetime().astimezone() if not ExcelProjectLoader._is_nan(row["ACTUAL END"]) else None,
                actual_start=pd.to_datetime(row["ACTUAL START"], errors="coerce").to_pydatetime().astimezone() if not ExcelProjectLoader._is_nan(row["ACTUAL START"]) else None,
                note=ExcelProjectLoader._coerce_str(row["NOTES"]),
                uuid=uuid,
                predecessor_ids=ExcelProjectLoader._coerce_str(row["PREDECESSOR"]).split(",") if not ExcelProjectLoader._is_nan(row["PREDECESSOR"]) else [],
                planned=ExcelProjectLoader._coerce_bool(row["PLANNED"]) if not ExcelProjectLoader._is_nan(row["PLANNED"]) else True,
                task_type=ExcelProjectLoader._infer_task_type(name),
            )

        phase_ctr = 1
        task_ctr = 1
        for _, row in df.iterrows():
            dur_cell = row["PLANNED DURATION (HOURS)"]
            if ExcelProjectLoader.is_phase_cell(dur_cell):
                # Commit previous phase implicitly by starting a new one
                new_phase = Phase(
                    name=ExcelProjectLoader._coerce_str(row["ACTIVITY"]),
                )
                new_phase.planned = ExcelProjectLoader._coerce_bool(row["PLANNED"]) if ExcelProjectLoader._is_nan(row["PLANNED"]) else True
                project.add_phase(new_phase)
                phase_ctr += 1
                task_ctr = 1
                current_phase = new_phase
            else:
                task = mk_task(row)
                task.infer_status()
                task_ctr += 1
                if current_phase is None:
                    # Task appears before any phase. Put it under an 'Unassigned' bucket
                    if unassigned_phase is None:
                        unassigned_phase = Phase(
                            name="Unassigned",
                            preceding_phase=None,
                        )
                        project.add_phase(unassigned_phase)
                        phase_ctr += 1
                    unassigned_phase.add_task(task)
                else:
                    current_phase.add_task(task)

        return project, metadata
    
    @staticmethod
    def load_metadata(wb, sheet_name: str="metadata") -> RelineMetadata:
        if not sheet_name in wb.sheetnames:
            raise ValueError(f"Provided sheet name {sheet_name} not found in Workbook.")
        ws = wb[sheet_name]

        site_id =          str(ws.cell(row=2,column=1).value)
        site_name =        str(ws.cell(row=2,column=2).value)
        mill_id =          str(ws.cell(row=2,column=3).value)
        mill_name =        str(ws.cell(row=2,column=4).value)
        vendor =           str(ws.cell(row=2,column=5).value)
        liner_system =     str(ws.cell(row=2,column=6).value)
        campaign_id =      str(ws.cell(row=2,column=7).value)
        scope =            str(ws.cell(row=2,column=8).value)
        liner =            str(ws.cell(row=2,column=9).value)
        supervisor =       str(ws.cell(row=2,column=10).value)
        notes =            str(ws.cell(row=2,column=11).value)
        
        return RelineMetadata(
            site_id=site_id,
            site_name=site_name,
            mill_id=mill_id,
            mill_name=mill_name,
            vendor=vendor,
            liner_system=liner_system,
            campaign_id=campaign_id,
            scope=scope,
            liner_type=liner,
            supervisor=supervisor,
            notes=notes,
        )


    @staticmethod
    def load_project_type(wb, sheet_name: str="Project Inputs") -> ProjectType:
        if not sheet_name in wb.sheetnames:
            raise ValueError(f"Provided sheet name {sheet_name} not found in Workbook.")
        
        ws = wb[sheet_name]
        
        type_str = str(ws.cell(row=13, column=4).value) # D13
        print(f"Read from 'Project Inputs' sheet for the type: {type_str}")
        proj_type = ProjectType.GENERIC
        match type_str:
            case "MILL_RELINE":
                return ProjectType.MILL_RELINE
            case "CIVIL":
                return ProjectType.CIVIL
            case "CRUSHER_REBUILD":
                return ProjectType.CRUSHER_REBUILD
            case _:
                return ProjectType.GENERIC
        return proj_type
    
    @staticmethod
    def load_project_id(wb, sheet_name: str = "Project Inputs") -> str:
        if not sheet_name in wb.sheetnames:
            raise ValueError(f"Provided sheet name {sheet_name} not found in Workbook.")

        ws = wb[sheet_name]
        val = ws.cell(row=14, column=4).value
        if val is None:
            return None
        return str(val)

    @staticmethod
    def load_project_settings(wb, sheet_name: str = "Project Inputs") -> ProjectSettings:
        
        if not sheet_name in wb.sheetnames:
            raise ValueError(f"Provided sheet name {sheet_name} not found in Workbook.")
        
        ws = wb[sheet_name]

        work_day_start_row = 5
        work_day_col = 4

        work_days = {
            "Sunday": False,
            "Monday": False,
            "Tuesday": False,
            "Wednesday": False,
            "Thursday": False,
            "Friday": False,
            "Saturday": False
        }

        work_days_idx = {
            1: "Sunday",
            2: "Monday",
            3: "Tuesday",
            4: "Wednesday",
            5: "Thursday",
            6: "Friday",
            7: "Saturday"
        }
        # get working days
        for row in range(work_day_start_row, work_day_start_row+7):
            idx = (row - work_day_start_row + 1) % 7
            work_days[work_days_idx[idx]] = True if ws.cell(row=row,column=work_day_col).value == "yes" else False

    @staticmethod
    def coerce_time(x) -> dt.time | None:
        if pd.isna(x):
            return None

        # If it's already a python time
        if isinstance(x, dt.time) and not isinstance(x, dt.datetime):
            return x

        # If it's a datetime / pandas Timestamp -> take the time part
        if isinstance(x, (dt.datetime, pd.Timestamp)):
            return x.time()

        # Excel numeric time (fraction of day)
        if isinstance(x, (int, float)):
            # 0.5 -> 12:00:00, etc.
            total_seconds = int(round(float(x) * 24 * 60 * 60))
            total_seconds %= 24 * 60 * 60
            hh, rem = divmod(total_seconds, 3600)
            mm, ss = divmod(rem, 60)
            return dt.time(hh, mm, ss)

        # Strings like "07:30" or "7:30 AM"
        if isinstance(x, str):
            s = x.strip()
            # Try a couple common formats
            for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p"):
                try:
                    return dt.datetime.strptime(s, fmt).time()
                except ValueError:
                    pass
            # Last resort: let pandas try
            t = pd.to_datetime(s, errors="coerce")
            if pd.isna(t):
                raise ValueError(f"Unrecognized time string: {x!r}")
            return t.time()

        raise TypeError(f"Unsupported time value type: {type(x)} ({x!r})")

    @staticmethod
    def load_shift_definition(file, project_id: str, sheet_name: str="shift_definition") -> ShiftDefinition:
        df = pd.read_excel(
            file,
            sheet_name=sheet_name,
            header=0,
            usecols="A:E",
            names=["project_id", "day_start_time", "night_start_time", "shift_length_hours", "timezone"]
        )

        df["day_start_time"] = df["day_start_time"].map(ExcelProjectLoader.coerce_time)
        df["night_start_time"] = df["night_start_time"].map(ExcelProjectLoader.coerce_time)
        if project_id is not None and (df["project_id"] != project_id).any():
            df["project_id"] = project_id # fall back on provided project id (existing project)

        return ShiftDefinition.from_df(df, project_id)
    
    @staticmethod
    def load_shift_assignments(file, project_id: str, sheet_name: str="shift_assignments") -> list[ShiftAssignment]:
        df = pd.read_excel(
            file,
            sheet_name=sheet_name,
            header=0,
            usecols="A:F",
            names=["id", "project_id", "shift_type", "crew_id", "start_date", "end_date"],
        )
        df["start_date"] = pd.to_datetime(df["start_date"], errors="raise").dt.to_pydatetime()
        df["end_date"] = pd.to_datetime(df["end_date"], errors="raise").dt.to_pydatetime()

        return ShiftAssignment.from_df(df, project_id=project_id)

