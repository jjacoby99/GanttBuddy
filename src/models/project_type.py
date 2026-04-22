from __future__ import annotations

from enum import Enum

class ProjectType(Enum):
    MILL_RELINE = 1
    CRUSHER_REBUILD = 2
    CIVIL=3
    GENERIC=4

def project_type_to_dict() -> dict[str, ProjectType]:
    return {" ".join([part.capitalize() for part in pt.name.split("_")]): pt for pt in list(ProjectType)}