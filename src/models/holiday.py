from __future__ import annotations
import requests
from datetime import date
from dataclasses import dataclass

@dataclass
class Holiday:
    name: str
    date: date

    def __str__(self):
        return f"{self.name} ({self.date})"
    

def fetch_holidays(year: int, province: str) -> list[Holiday]:
    url = f"https://www.officeholidays.com/ics/ics_country.php?tbl_country=Canada&tbl_province={province}&year={year}"
    response = requests.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch holidays: {response.status_code}")
    
    data = response.json()
    holidays = []
    for holiday in data['province']['holidays']:
        stat = Holiday(
            name=holiday['nameEn'],
            date=date.fromisoformat(holiday['observedDate'])
        )
        holidays.append(stat)
    return holidays