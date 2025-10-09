import json
import os
from models.project import Project
from models.phase import Phase
from models.project_settings import ProjectSettings
from pprint import pprint

class ProjectLoader():
    @staticmethod
    def load_json_file(file_path: str) -> dict:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File '{file_path}' not found.")
        if not os.path.splitext(file_path)[1].lower() == ".json":
            raise ValueError(f"File '{file_path}' is not a .json file.")
        
        with open(file_path, "r") as f:
            proj_dict = json.load(f)
        
        return proj_dict

    @staticmethod
    def load_project(proj_dict: dict) -> Project:
        for key in ["name", "phases", "settings"]:
            if not key in proj_dict:
                raise ValueError(f"Key '{key}' not found in project dictionary.")
            
        project = Project(name=proj_dict["name"], description=proj_dict.get("description", ""))
        
        phases = [Phase.from_dict(phase_dict) for phase_dict in proj_dict["phases"]]
        
        if len(phases) > 1:
            for i, phase in enumerate(phases[1:]):
                if phase.preceding_phase:
                    pass




        project.settings = ProjectSettings.from_dict(proj_dict["settings"])

        return project