import datetime as dt
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from models.organization import OrganizationMembership


class User(BaseModel):
    id: str
    email: EmailStr
    name: str
    is_active: bool
    created_at: dt.datetime
    auth_provider: str
    last_login_at: dt.datetime | None = None
    roles: list[dict[str, Any]] = Field(default_factory=list)
    organizations: list[OrganizationMembership] = Field(default_factory=list)
