from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
from typing import Literal

import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd

class Rotation(Enum):
    TWODAY_TWONIGHT=0, # 2 days, 2 nights schedule, 4 on 4 off

ARB_DATE = dt.date(year=2000,month=1,day=1)

@dataclass
class Shift:
    start: dt.time = field(default=dt.time(hour=7))
    duration: dt.timedelta = field(default=dt.timedelta(hours=12))

    crew: str = field(default_factory=str)
    shift_type: Literal["day", "night"] = field(default="day")

    @property
    def end(self) -> dt.time:
        base = dt.datetime.combine(ARB_DATE, self.start)
        return (base + self.duration).time()

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "duration": self.duration,
            "crew": self.crew,
            "shift_type": self.shift_type
        }
    
    def from_dict(self, data: dict) -> None:
        for key in ["start", "duration", "crew", "shift_type"]:
            if key not in data:
                raise KeyError(f"Required key: {key} not in provided data: {data}")
        
        self.start = data.get("start", dt.time(hour=7))
        self.duration = data.get("duration", dt.timedelta(hours=12))
        self.crew = data.get("crew", "")
        self.shift_type = data.get("shift_type", "day")

@dataclass
class ShiftSchedule:
    timezone: ZoneInfo = field(default=ZoneInfo("America/Vancouver"))
    shifts: list[Shift] = field(default_factory=list)

    @staticmethod
    def from_df(df: pd.DataFrame) -> ShiftSchedule:
        required = ["crew", "start", "end", "shift_type"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise KeyError(f"Provided dataframe is missing required columns: {missing}")

        sched = ShiftSchedule()

        for _, row in df.iterrows():
            start = dt.datetime.combine(ARB_DATE, row["start"])
            end = dt.datetime.combine(ARB_DATE, row["end"])

            dur = end - start
            if dur.total_seconds() <= 0:
                dur += dt.timedelta(days=1) # account for night shift
            
            sched.shifts.append(
                Shift(
                    start=row["start"],
                    duration=dur,
                    crew=row["crew"],
                    shift_type=row["shift_type"]
                )
            )

        return sched

    def to_dict(self) -> dict:
        data = {
            "start": [],
            "duration": [],
            "end": [],
            "crew": [],
            "shift_type": []
        }
        
        for shift in self.shifts:
            data["start"].append(shift.start)
            data["duration"].append(shift.duration)
            data["crew"].append(shift.crew)
            data["shift_type"].append(shift.shift_type)

            combined = dt.datetime.combine(ARB_DATE, shift.start)
            data["end"].append((combined + shift.duration).time())

        return data

    def to_project_shift_config_payload(self) -> list[dict]:
        """
        Convert ShiftSchedule into backend-compatible
        per-crew configs: day_start_time, night_start_time, shift_length_hours, timezone.
        """
        by_crew: dict[str, dict[str, Shift]] = defaultdict(dict)

        for s in self.shifts:
            if not s.crew:
                raise ValueError("Shift.crew is required")
            by_crew[s.crew][s.shift_type] = s

        payload: list[dict] = []
        for crew, shifts in by_crew.items():
            day = shifts.get("day")
            night = shifts.get("night")

            if day is None or night is None:
                raise ValueError(f"Crew '{crew}' must have both day and night shifts")

            # durations must match (backend has shift_length_hours)
            day_h = day.duration.total_seconds() / 3600.0
            night_h = night.duration.total_seconds() / 3600.0
            if abs(day_h - night_h) > 1e-6:
                raise ValueError(f"Crew '{crew}' day/night shift durations differ ({day_h} vs {night_h})")

            payload.append({
                "crew": crew,
                "day_start_time": day.start.isoformat(),
                "night_start_time": night.start.isoformat(),
                "shift_length_hours": day_h,
                "timezone": str(self.timezone.key) if hasattr(self.timezone, "key") else str(self.timezone),
            })

        return payload
