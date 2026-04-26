from logic.backend.api_client import fetch_projects

from models.project_summary import ProjectSummary

def get_projects(headers: dict, n_proj: int=-1, include_closed: bool = False) -> dict[str, ProjectSummary]:
    """
        Returns a dict of project_id: project summary.
    """
    if n_proj < -1:
        raise ValueError(f"n_proj must be positive (or -1 for all projects)")
    try:
        resp = fetch_projects(headers, include_closed=include_closed)
    except Exception as e:
        raise e
    
    if n_proj != -1:
        resp = resp[:n_proj]

    to_return: dict[str, ProjectSummary] = {}
    for proj in resp:
        summary = ProjectSummary.model_validate(proj)
        to_return[summary.id] = summary

    return to_return
