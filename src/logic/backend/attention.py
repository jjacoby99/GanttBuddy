from logic.backend.api_client import fetch_attention_tasks
from models.input.task import TaskIn, AttentionIn


def get_attention_tasks(headers: dict) -> AttentionIn:
    """
        Returns AttentionIn model containing three lists of TaskIn. Late tasks, tasks awaiting actuals
    """

    try:
        json = fetch_attention_tasks(headers)
    except Exception:
        return None
    
    late = json.get("late_tasks", [])
    upcoming = json.get("upcoming_tasks", [])
    awaiting = json.get("awaiting_actuals", [])

    late = [TaskIn.model_validate(task) for task in late]
    upcoming = [TaskIn.model_validate(task) for task in upcoming]
    awaiting = [TaskIn.model_validate(task) for task in awaiting]

    return AttentionIn(
        late=late,
        upcoming=upcoming,
        awaiting=awaiting
    )