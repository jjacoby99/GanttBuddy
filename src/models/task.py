from __future__ import annotations
from datetime import datetime, date, timedelta
from typing import Optional
from dataclasses import dataclass
from models.project_settings import ProjectSettings
from exceptions.date_error import InvalidDateError
from exceptions.time_error import InvalidTimeError
from logic.generate_id import new_id

@dataclass
class Task:
    uuid: str = new_id()
    name: str
    start_date: datetime
    end_date: datetime
    note: str
    preceding_task: Optional[Task] = None

    def to_dict(self) -> dict:
        return {"Task": self.name, 
                "Start": self.start_date, 
                "Finish": self.end_date, 
                "Note": self.note,
                "preceding_task": self.preceding_task.name if self.preceding_task else None,
                "uuid": self.uuid}
    
    def __str__(self) -> str:
        return f"Task(name = {self.name}, start_date={self.start_date}, end_date={self.end_date}, note={self.note})"
    
    @staticmethod
    def from_dict(data: dict) -> Task:
        if not "Task" in data:
            raise ValueError("Task must have a name.")
        if not "Start" in data:
            raise ValueError("Task must have a start date.")
        if not "Finish" in data:   
            raise ValueError("Task must have an end date.")
            
        task = Task.__new__(Task)  # Create an uninitialized instance
        task.name = data["Task"]
        task.start_date = data["Start"]
        task.end_date = data["Finish"]
        task.note = data.get("note", "")
        task.preceding_task = data.get("preceding_task", None)
        task.uuid = data.get("uuid", new_id())
        return task

    def calculate_end_date(self, duration: int, settings: ProjectSettings) -> datetime:
        """
            Calculate the end date of a task given a start date, duration (in days), and project settings.
            This function takes into account working hours, working days, and holidays based on the provided settings.

            if the start_date is on a holiday or weekend, a DateError is raised.

            if the start_date time is outside of working hours, a TimeError is raised.
        """

        if not settings.is_working_day(self.start_date):
            raise InvalidDateError(f"Start date {self.start_date.date()} is not a working day.")
        
        if settings.is_holiday(self.start_date):
            raise InvalidDateError(f"Start date {self.start_date.date()} is a holiday.")
        
        if not settings.within_working_hours(self.start_date.time()):
            raise InvalidTimeError(f"Start time {self.start_date.time()} is outside of working hours ({settings.work_start_time} - {settings.work_end_time}).")
        pass
    
        #current_date = self.start_date
        #day_remaining = settings.work_end_time - self.start_date.time()
        #time_allocated = day_remaining
        #while time_allocated < duration:
            
        #    current_date += datetime.timedelta(days=1)
        #    if settings.is_working_day(current_date) and not settings.is_holiday(current_date):
        #        days_added += 1
        
        #return current_date

