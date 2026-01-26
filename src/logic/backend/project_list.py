from logic.backend.api_client import fetch_projects

def get_projects(headers) -> dict[str, str]:
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
    
        to_return[id] = name
    
    return to_return
