from logic.backend.api_client import fetch_crews

from models.crew import CrewIn


def get_crews(headers: dict, site_id: str) -> list[CrewIn]:

    try:
        data = fetch_crews(headers=headers, site_id=site_id)
    except ValueError as e:
        raise e
    crews = []
    for crew_dict in data:
        id = crew_dict.get("id")
        site_id = crew_dict.get("site_id")
        name = crew_dict.get("name")
        members = crew_dict.get("members", None)

        crews.append(
            CrewIn(
                id=id,
                site_id=site_id,
                name=name,
                members=members
            )
        )
    return crews
