from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class Organization(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool
    created_at: dt.datetime
    created_by_user_id: str


class OrganizationMembership(BaseModel):
    organization_id: str
    user_id: str
    role: str
    joined_at: dt.datetime
    invited_by_user_id: str | None = None
    is_active: bool
    organization: Organization | None = None
