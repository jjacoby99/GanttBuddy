from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from models.holiday import Holiday, fetch_holidays
from functools import lru_cache
from typing import Optional

@dataclass
class ProjectSettings:
    work_all_day: bool = False
    work_start_time: Optional[time] = time(hour=7, minute=0)  # 7:00 AM
    work_end_time: Optional[time] = time(hour=18, minute=0)   # 5:00 PM
    working_days: tuple[bool]  = (True, True, True, True, False, False, False) # 0=Monday, 6=Sunday
    observe_state_holidays: bool = True
    province: Optional[str] = None   # Default province for holidays
    holidays: list[Holiday] = None

    @property
    def work_duration(self) -> datetime.timedelta:
        if self.work_all_day:
            return timedelta(hours=24)
        return self.work_end_time - self.work_start_time

    def is_working_day(self, date: datetime) -> bool:
        return self.working_days[date.weekday()]
    
    def within_working_hours(self, time: datetime.time) -> bool:
        return self.work_start_time <= time <= self.work_end_time
    
    @lru_cache(maxsize=32)
    def get_holidays(self, year) -> list[Holiday]:
        if not self.observe_state_holidays:
            return []
        
        try:
            holidays = fetch_holidays(year, self.province)
            self.holidays = holidays
        except RuntimeError as e:
            print(f"Warning: Could not fetch holidays for {self.province} in {year}: {e}")
            return []
        return holidays

    def is_holiday(self, date: datetime) -> bool:
        if not self.observe_state_holidays:
            return False
        
        # check if we already have holidays for this year
        if self.holidays and date.year in [h.date.year for h in self.holidays]:
            for holiday in self.holidays:
                if holiday.date == date.date():
                    return True
            return False
        
        # fetch holidays for this year
        holidays = self.get_holidays(date.year)
        if holidays == []:
            return False
        
        for holiday in holidays:
            if holiday.date == date.date():
                return True
        return False