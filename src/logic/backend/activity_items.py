from dataclasses import dataclass
import datetime as dt
from zoneinfo import ZoneInfo
from typing import Literal

from logic.backend.api_client import fetch_attention_tasks

@dataclass
class AttentionItem:
    project_id: str
    project_name: str
    severity: str  # "late" | "due_soon" | "awaiting_actuals" | "info"
    title: str
    count: int
    due_hint: str  # e.g. "Next 48h", "Overdue", "This week"


def infer_due_hint(variance: dt.timedelta) -> str:
    if variance < dt.timedelta(0):
        return "Overdue" 

    if variance < dt.timedelta(hours=2):
        return "Due soon (< 2h)"
    
    if variance < dt.timedelta(days=1):
        return "Next 24h"

    if variance < dt.timedelta(days=2):
        return "Next 48h"
    
    if variance < dt.timedelta(days=7):
        return "This Week"

    return "Weeks Out"

def get_attention_list(task_list: list, severity: Literal["late", "due_soon", "awaiting_actuals", "info"], timezone: ZoneInfo):
    out = []
    for el in task_list:
        pid = el.get("project_id", "")
        p_name = el.get("project_name")
        t_name = el.get("name", "")

        pe = el.get("planned_end")
        pe = dt.datetime.fromisoformat(pe.replace("Z", "+00:00")).astimezone(timezone)
        
        variance = pe - dt.datetime.now(timezone)
        out.append(
            AttentionItem(
                project_id=pid,
                project_name=p_name,
                severity=severity,
                title=t_name,
                count=1,
                due_hint=infer_due_hint(variance=variance)
            )
        )
    return out

def get_attention_items(headers, timezone: ZoneInfo) -> list[AttentionItem]:
    try:
        resp = fetch_attention_tasks(headers)
    except Exception:
        return []
    
    late = resp.get("late_tasks", [])
    upcoming = resp.get("upcoming_tasks", [])
    awaiting = resp.get("awaiting_actuals", [])

    attention_items = []
    attention_items += get_attention_list(
        task_list=late,
        severity="late",
        timezone=timezone
    )

    attention_items += get_attention_list(
        task_list=upcoming,
        severity="due_soon",
        timezone=timezone
    )
        
    attention_items += get_attention_list(
        task_list=awaiting,
        severity="awaiting_actuals",
        timezone=timezone
    )

    return attention_items


def count_activities(needs: list[AttentionItem]) -> dict:
    # st.metric("Late tasks", kpis["late_tasks"])
    # st.metric("Awaiting actuals", kpis["awaiting_actuals"])
    # st.metric("Due soon (48h)", kpis["due_soon_tasks"])
    late = 0
    awaiting = 0
    due_soon = 0

    for need in needs:
        late += 1 if need.severity == "late" else 0
        awaiting += 1 if need.severity == "awaiting_actuals" else 0
        due_soon += 1 if need.severity == "due_soon" else 0
    
    return {
        "late_tasks": late,
        "awaiting_actuals": awaiting,
        "due_soon_tasks": due_soon
    }


