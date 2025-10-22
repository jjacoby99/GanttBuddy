import json
import os
import pandas as pd
from models.project import Project
from models.phase import Phase
from models.project_settings import ProjectSettings
from models.task import Task
from pprint import pprint
import math
from dataclasses import dataclass, field
from typing import Any, Optional
import re
from openpyxl import load_workbook
from io import BytesIO
from typing import Union

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
    def load_excel_project(file, params: ExcelParameters) -> Project:
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

        # Drop fully empty rows based on ACTIVITY being blank
        df["ACTIVITY"] = df["ACTIVITY"].astype(str).str.strip()
        df = df[df["ACTIVITY"] != ""].reset_index(drop=True)
        
        wb = load_workbook(bio_opx, read_only=True, data_only=True)
        plan_sheet = wb[params.sheet_name]
        proj_name = plan_sheet[params.project_name_cell].value

        project = Project(name=proj_name if proj_name else "Untitled Project")
        current_phase = None
        unassigned_phase = None

        def mk_task(row)-> Task:
            uuid = ExcelProjectLoader._coerce_str(row["UUID"])
            if uuid == "":
                from models.task import new_id
                uuid = new_id()

            return Task(
                name=ExcelProjectLoader._coerce_str(row["ACTIVITY"]),
                start_date=pd.to_datetime(row["PLANNED START"], errors="coerce") if not ExcelProjectLoader._is_nan(row["PLANNED START"]) else None,
                end_date=pd.to_datetime(row["PLANNED END"], errors="coerce") if not ExcelProjectLoader._is_nan(row["PLANNED END"]) else None,
                actual_end=pd.to_datetime(row["ACTUAL END"], errors="coerce") if not ExcelProjectLoader._is_nan(row["ACTUAL END"]) else None,
                actual_start=pd.to_datetime(row["ACTUAL START"], errors="coerce") if not ExcelProjectLoader._is_nan(row["ACTUAL START"]) else None,
                note=ExcelProjectLoader._coerce_str(row["NOTES"]),
                uuid=uuid,
                predecessor_ids=ExcelProjectLoader._coerce_str(row["PREDECESSOR"]).split(",") if not ExcelProjectLoader._is_nan(row["PREDECESSOR"]) else [],
            )

        phase_ctr = 1
        task_ctr = 1
        for _, row in df.iterrows():
            dur_cell = row["PLANNED DURATION (HOURS)"]
            if ExcelProjectLoader.is_phase_cell(dur_cell):
                # Commit previous phase implicitly by starting a new one
                new_phase = Phase(
                    name=str(phase_ctr) + ". " + ExcelProjectLoader._coerce_str(row["ACTIVITY"]),
                )
                project.add_phase(new_phase)
                phase_ctr += 1
                task_ctr = 1
                current_phase = new_phase
            else:
                task = mk_task(row)
                task.name = f"{phase_ctr - 1}.{task_ctr} " + task.name
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

        return project
    
    @staticmethod
    def load_project_settings(file, sheet_name: str = "Project Inputs") -> ProjectSettings:
        data = BytesIO(file.read())
        
        wb = load_workbook(data, read_only=True, data_only=True)

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

        # get working hours


        
        
