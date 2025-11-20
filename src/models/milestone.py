from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

@dataclass
class Milestone:
    name: str = field(default_factory=str) 
    timestamp: datetime = field(default_factory=datetime)
    predecessor_type: Literal["Phase", "Task"]
    predecessors: list[str] = field(default_factory=list) # list of uuid predecessors (task)




