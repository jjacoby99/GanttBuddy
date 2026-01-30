from logic.backend.api_client import fetch_projects
import datetime as dt

def get_projects(headers: dict, n_proj: int=-1) -> dict:
    """
        Returns a dict of project_id: project_name
    """
    if n_proj < -1:
        raise ValueError(f"n_proj must be positive (or -1 for all projects)")
    try:
        resp = fetch_projects(headers)
    except Exception as e:
        raise e
    
    if n_proj != -1:
        resp = resp[:n_proj]

    to_return = {}
    for proj in resp:
        id = proj.get("id", None)
        name = proj.get("name", None)
        description = proj.get("description", None)

        created = proj.get("created_at", None)
        if created:
            dt_created = dt.datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    
        updated = proj.get("updated_at", None)
        if updated:
            dt_updated = dt.datetime.fromisoformat(updated.replace("Z", "+00:00")).astimezone(dt.timezone.utc)

        start = proj.get("planned_start", None)
        if start:
            start_dt = dt.datetime.fromisoformat(updated.replace("Z", "+00:00")).astimezone(dt.timezone.utc)

        end = proj.get("planned_finish", None)
        if start:
            end_dt = dt.datetime.fromisoformat(updated.replace("Z", "+00:00")).astimezone(dt.timezone.utc)

        to_return[id] = {
            "name": name,
            "description": description,
            "created": dt_created,
            "updated": dt_updated,
            "planned_start": start_dt,
            "planned_finish": end_dt
        }
    
    return to_return
