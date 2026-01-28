from logic.backend.api_client import fetch_projects
import datetime as dt

def get_projects(headers) -> dict:
    """
        Returns a dict of project_id: project_name
    """

    try:
        resp = fetch_projects(headers)
    except Exception as e:
        raise e
    
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

        to_return[id] = {
            "name": name,
            "description": description,
            "created": dt_created,
            "updated": dt_updated
        }
    
    return to_return
