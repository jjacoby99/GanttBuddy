from __future__ import annotations

from pydantic import BaseModel
import datetime as dt

class SiteIn(BaseModel):
    code: str
    name: str
    timezone: str
    is_active: bool
    id: str
    created_at: dt.datetime
    updated_at: dt.datetime

    @staticmethod
    def by_id(sites: list[SiteIn]) -> dict[str, SiteIn]:
        """
            Maps sites by their ID to the SiteIn object.
        """
        return {site.id: site for site in sites}
    

class SiteOut(BaseModel):
    code: str
    name: str
    timezone: str
    is_active: bool