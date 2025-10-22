from models.phase import Phase
from models.task import Task
from models.project import Project
from models.project_settings import ProjectSettings
from models.session import SessionModel
import pandas as pd

def build_forecast_df(project: Project) -> pd.DataFrame:
    """
        Reads from project, returns a formatted dataframe for use in forecasting 
    """ 
    if not project.phases:
        raise ValueError(f"Provided project {project.name} has no phases.")
    
    if not project.has_task:
        raise ValueError(f"Provided project {project.name} has no tasks")
    
    pd.set_option("display.float_format", "{:.2f}".format)

    data = {
        "UUID": [],
        "Phase": [],
        "Task": [],
        "Est. Duration (h)": [],
        "Planned Start": [],
        "Planned End": [],
        "Actual Start": [],
        "Actual End": [],
        "% Complete": [],
        "Notes": []
    }
    

    for phase in project.phases.values():
        for task in phase.tasks.values():
            data["UUID"].append(task.uuid)
            data["Phase"].append(phase.name)
            data["Task"].append(task.name)
            data["Est. Duration (h)"].append(float((task.end_date - task.start_date).total_seconds() / 3600.0))
            data["Planned Start"].append(task.start_date)
            data["Planned End"].append(task.end_date)
            data["Actual Start"].append(task.actual_start if task.actual_start else pd.NaT)
            data["Actual End"].append(task.actual_end if task.actual_end else pd.NaT)
            data["% Complete"].append(0.0)
            data["Notes"].append(task.note)

    return pd.DataFrame(data)
    