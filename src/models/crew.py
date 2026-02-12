from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
import pandas as pd

class CrewIn(BaseModel):
    id: str
    site_id: str
    name: str

    members: Optional[int] = None 

    @staticmethod
    def to_df(crews: list[CrewIn]) -> pd.DataFrame:
        data = {
            "id": [],
            "site_id": [],
            "name": [],
            "members": []
        }

        for crew in crews:
            data["id"].append(crew.id)
            data["site_id"].append(crew.site_id)
            data["name"].append(crew.name)
            data["members"].append(crew.members if crew.members else None)

        return pd.DataFrame(data)


class CrewOut(BaseModel):
    site_id: str
    name: str
    members: Optional[int] = None
