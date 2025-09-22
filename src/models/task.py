from __future__ import annotations
import datetime
from typing import Optional
from dataclasses import dataclass

@dataclass
class Task:
    name: str
    start_date: datetime
    end_date: datetime
    note: str
    preceding_task: Optional[Task] = None

    def to_dict(self) -> dict:
        return {"Task": self.name, "Start": self.start_date, "Finish": self.end_date, "Note": self.note}
    
    def __str__(self) -> str:
        return f"Task(name = {self.name}, start_date={self.start_date}, end_date={self.end_date}, note={self.note})"