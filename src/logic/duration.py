from models.project_settings import ProjectSettings
from models.project import Project
from models.task import Task
from models.phase import Phase
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class DurationCalculator:
    settings: ProjectSettings

    def duration(self, start_date: datetime, end_date: datetime) -> float:
        if end_date < start_date:
            raise ValueError(f"Provided end date {end_date.strftime("%Y-%m-%d %H:%M")} precedes start date {start_date.strftime("%Y-%m-%d %H:%M")}")
        
        # todo
        # implement settings specific duration calculation
        # needs to incorperate:
        #   - working days
        #   - working hours
        #   - holidays (if respected)
        #   - weekends (if respected)
        return (end_date - start_date).total_seconds() / 3600