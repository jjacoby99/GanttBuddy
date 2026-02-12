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