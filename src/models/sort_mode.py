from enum import Enum
class SortMode(str, Enum):
    manual="manual"
    by_planned_start = "by_planned_start"
    by_actual_start = "by_actual_start"
    alphabetical = "alphabetical"