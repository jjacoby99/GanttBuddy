from models.crew import CrewOut
from logic.backend.api_client import post_new_crew

def post_crew(headers: dict, crew: CrewOut) -> CrewOut:

    try:
        response = post_new_crew(headers=headers, crew=crew)
    except ValueError as e:
        print(f"Failed to create new crew: {str(e)}")
        raise ValueError(f"Failed to create new crew {crew.name}")
    
    out = CrewOut(**response)
    return out
