from __future__ import annotations

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal

class RelineMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")  # no rogue keys
    
    schema_version: int = 1

    site_id: str
    site_name: str
    mill_id: str
    mill_name: str
    vendor: str
    liner_system: str

    campaign_id: Optional[str] = None
    scope: Optional[Literal["Full", "Partial", "Other"]] = None
    liner_type: Optional[str] = None
    template_version: Optional[str] = None

    supervisor: str = Field(default_factory=str)
    crew_count_day: Optional[int] = Field(default=None, ge=0)
    crew_count_night: Optional[int] = Field(default=None, ge=0)

    notes: str = Field(default_factory=str)

KEYMAP_RELINE = {
    "site": "reline.site",
    "mill_id": "reline.mill_id",
    "vendor": "reline.vendor",
    "liner_system": "reline.liner_system",
    "campaign_id": "reline.campaign_id",
    "scope": "reline.scope",
    "liner_type": "reline.liner_type",
    "template_version": "reline.template_version",
    "crew_count_day": "reline.crew_count_day",
    "crew_count_night": "reline.crew_count_night",
}
