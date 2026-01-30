from dataclasses import dataclass
import datetime as dt

from logic.backend.api_client import fetch_attention_tasks

@dataclass
class AttentionItem:
    project_id: str
    project_name: str
    severity: str  # "late" | "due_soon" | "awaiting_actuals" | "info"
    title: str
    count: int
    due_hint: str  # e.g. "Next 48h", "Overdue", "This week"


def get_attention_items(headers) -> list[AttentionItem]:
    try:
        resp = fetch_attention_tasks(headers)
    except Exception:
        return []
    
    late = resp.get("late_tasks", [])
    upcoming = resp.get("upcoming_tasks", [])
    awaiting = resp.get("awaiting_actuals", [])

    attention_items = []
    for el in late:
        pid = el.get("project_id", "")
        p_name = el.get("project_name")
        t_name = el.get("name", "")
        ps = el.get("planned_start")
        ps = dt.datetime.fromisoformat(ps.replace("Z", "+00:00")).astimezone(dt.timezone.utc)

        pe = el.get("planned_end")
        pe = dt.datetime.fromisoformat(pe.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        
        attention_items.append(
            AttentionItem(
                project_id=pid,
                project_name=p_name,
                severity="late",
                title=t_name,
                count=1,
                due_hint=pe
            )
        )

    for el in upcoming:
        pid = el.get("project_id", "")
        p_name = el.get("project_name")
        t_name = el.get("name", "")
        ps = el.get("planned_start")
        ps = dt.datetime.fromisoformat(ps.replace("Z", "+00:00")).astimezone(dt.timezone.utc)

        pe = el.get("planned_end")
        pe = dt.datetime.fromisoformat(pe.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        
        attention_items.append(
            AttentionItem(
                project_id=pid,
                project_name=p_name,
                severity="due_soon",
                title=t_name,
                count=1,
                due_hint=pe
            )
        )

    for el in awaiting:
        pid = el.get("project_id", "")
        p_name = el.get("project_name")
        t_name = el.get("name", "")

        ps = el.get("planned_start")
        ps = dt.datetime.fromisoformat(ps.replace("Z", "+00:00")).astimezone(dt.timezone.utc)

        pe = el.get("planned_end")
        pe = dt.datetime.fromisoformat(pe.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
        
        attention_items.append(
            AttentionItem(
                project_id=pid,
                project_name=p_name,
                severity="awaiting_actuals",
                title=t_name,
                count=1,
                due_hint=pe
            )
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


