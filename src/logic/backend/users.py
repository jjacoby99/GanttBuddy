from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

import pydantic

from logic.backend.api_client import get_current_user
from models.user import User

_TIMESTAMP_KEYS = {"created_at", "last_login_at", "joined_at"}


def _parse_backend_timestamp(value: str, timezone: ZoneInfo) -> dt.datetime:
    normalized = value.replace("Z", "+00:00")

    try:
        timestamp = dt.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid backend timestamp: {value}") from exc

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=dt.UTC)

    return timestamp.astimezone(timezone)


def _convert_backend_timestamps(value: Any, timezone: ZoneInfo, *, field_name: str | None = None) -> Any:
    if isinstance(value, dict):
        return {
            key: _convert_backend_timestamps(item, timezone, field_name=key)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_convert_backend_timestamps(item, timezone, field_name=field_name) for item in value]

    if isinstance(value, str) and field_name in _TIMESTAMP_KEYS:
        return _parse_backend_timestamp(value, timezone)

    return value


def get_user(auth_headers: dict, timezone: ZoneInfo) -> User:
    if not auth_headers:
        raise ValueError("Auth headers are required to fetch the current user.")

    if not isinstance(timezone, ZoneInfo):
        raise TypeError("timezone must be a ZoneInfo instance.")

    user_data = get_current_user(auth_headers=auth_headers)
    normalized_user_data = _convert_backend_timestamps(user_data, timezone)

    try:
        return User.model_validate(normalized_user_data)
    except pydantic.ValidationError as exc:
        raise ValueError("Backend user payload did not match the expected User schema.") from exc
