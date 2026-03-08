from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, TypeAdapter, Field
from typing import Optional, Any
import datetime as dt
import pandas as pd
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo


LOCAL_TZ = ZoneInfo("America/Vancouver")


class DelayType(str, Enum):
    PERFORMANCE = "PERFORMANCE"
    EQUIPMENT = "EQUIPMENT"
    SAFETY = "SAFETY"
    FOUND_WORK = "FOUND_WORK"
    PREPARATION = "PREPARATION"
    MANPOWER_SHORTAGE = "MANPOWER_SHORTAGE"
    OTHER = "OTHER"

DELAY_BADGE: dict[DelayType, tuple[str, str, str]] = {
    DelayType.PERFORMANCE:        ("blue",   ":material/speed:",             "Performance"),
    DelayType.EQUIPMENT:          ("violet", ":material/construction:",      "Equipment"),
    DelayType.SAFETY:             ("red",    ":material/health_and_safety:", "Safety"),
    DelayType.FOUND_WORK:         ("green",  ":material/search:",            "Found work"),
    DelayType.PREPARATION:        ("yellow", ":material/checklist:",         "Preparation"),
    DelayType.MANPOWER_SHORTAGE:  ("orange", ":material/group_remove:",      "Manpower shortage"),
    DelayType.OTHER:              ("gray",   ":material/more_horiz:",        "Other"),
}
 

class Delay(BaseModel):
    id: str
    project_id: str
    delay_type: DelayType
    duration_minutes: int
    description: str

    start_dt: Optional[dt.datetime]
    end_dt: Optional[dt.datetime]

    shift_assignment_id: Optional[str]

    created_by: str
    created_at: dt.datetime

    updated_at: Optional[dt.datetime]
    updated_by: Optional[str]

    @staticmethod
    def to_df(delays: list[Delay]) -> pd.DataFrame:
        return pd.DataFrame([m.model_dump() for m in delays])
    
    @staticmethod
    def from_df(df: pd.DataFrame) -> list[Delay]:

        # Normalize:

        records = df.to_dict(orient="records")

        records = [
            {k: (None if pd.isna(v) else v) for k, v in r.items()}
            for r in records
        ]


        return TypeAdapter(list[Delay]).validate_python(records)

class DelayEditorRow(BaseModel):
    """
    Row model used for Streamlit data_editor.
    Keep it limited to editable fields (+ id for updates).
    """
    id: Optional[str] = None  # None/new row => backend creates

    client_id: UUID = Field(default_factory=uuid4, exclude=True) # don't include in model_dump
    delay_type: DelayType = DelayType.OTHER
    duration_minutes: int = Field(default=30, ge=1)
    description: str = ""

    start_dt: Optional[dt.datetime] = None
    end_dt: Optional[dt.datetime] = None

    shift_assignment_id: Optional[str] = None

    def key(self) -> tuple[str, UUID]:
        # Prefer DB id when present; otherwise client_id
        return ("db", self.id) if self.id is not None else ("client", self.client_id)
    
    @staticmethod   
    def from_delay(delays: list[Delay]) -> list[DelayEditorRow]:
        return [
            DelayEditorRow(
                id=d.id,
                client_id=uuid4(),
                delay_type=d.delay_type,
                duration_minutes=d.duration_minutes,
                description=d.description,
                start_dt=d.start_dt,
                end_dt=d.end_dt,
                shift_assignment_id=d.shift_assignment_id,
            )
            for d in delays
        ]
    @staticmethod
    def empty_df() -> pd.DataFrame:
        # Explicit dtypes = predictable Streamlit editor behavior
        return pd.DataFrame({
            "id": pd.Series(dtype="object"),  # UUID as string
            "client_id": pd.Series(dtype="object"),
            "delay_type": pd.Series(dtype="object"),  # enum/string
            "duration_minutes": pd.Series(dtype="int64"),
            "description": pd.Series(dtype="string"),
            "start_dt": pd.Series(dtype="datetime64[ns]"),
            "end_dt": pd.Series(dtype="datetime64[ns]"),
            "shift_assignment_id": pd.Series(dtype="object"),  # UUID as string
        })
    
    @staticmethod
    def to_df(rows: list["DelayEditorRow"]) -> pd.DataFrame:
        if not rows:
            return DelayEditorRow.empty_df()
        return pd.DataFrame([r.model_dump() for r in rows])

    @staticmethod
    def from_df(df: pd.DataFrame) -> list[DelayEditorRow]:
        records = df.to_dict(orient="records")
        records = [
            {k: (None if pd.isna(v) else v) for k, v in r.items()}
            for r in records
        ]

        for r in records:
            # Convert pandas timestamps
            for k in ("start_dt", "end_dt"):
                v = r.get(k)
                if hasattr(v, "to_pydatetime"):
                    r[k] = v.to_pydatetime()

            #ensure client_id is never None
            if not r.get("client_id"):
                r["client_id"] = str(uuid4())  # pydantic parses to UUID

            # You will likely want these too (same “None blocks defaults” issue):
            if r.get("delay_type") is None:
                r["delay_type"] = DelayType.OTHER
            if r.get("duration_minutes") is None:
                r["duration_minutes"] = 30
            if r.get("description") is None:
                r["description"] = ""

        return TypeAdapter(list[DelayEditorRow]).validate_python(records)

    @staticmethod
    def _cmp_dump(row: "DelayEditorRow") -> dict[str, Any]:
        # Compare “meaningful” fields only.
        # Exclude ids (and any other volatile fields like timestamps, computed fields, etc.)
        return row.model_dump(exclude={"id"}, exclude_none=False)

    @staticmethod
    def diff(delays_in: list[DelayEditorRow], delays_out: list[DelayEditorRow],) -> dict[str, Any]:
        before = {r.key(): r for r in delays_in}
        after  = {r.key(): r for r in delays_out}

        removed_keys = before.keys() - after.keys()
        added_keys   = after.keys() - before.keys()
        common_keys  = before.keys() & after.keys()

        removed = [before[k] for k in removed_keys]
        added   = [after[k] for k in added_keys]

        modified: list[dict[str, "DelayEditorRow"]] = []
        for k in common_keys:
            b = before[k]
            a = after[k]
            if DelayEditorRow._cmp_dump(b) != DelayEditorRow._cmp_dump(a):
                modified.append({"before": b, "after": a})

        return {"removed": removed, "added": added, "modified": modified}