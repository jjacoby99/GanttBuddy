from dataclasses import dataclass, field
import datetime as dt

class ConstraintTypeBase:
    name: str
    code: str
    
    def __init__(self, name: str, code: str):
        self.name = name
        self.code = code
    

class FinishToStart(ConstraintTypeBase):
    code = "FS"
    name = "Finish to Start"

    def __init__(self):
        super().__init__(name=self.name, code=self.code)
    

class FinishToFinish(ConstraintTypeBase):
    code = "FF"
    name = "Finish to Finish"

    def __init__(self):
        super().__init__(name=self.name, code=self.code)


class StartToStart(ConstraintTypeBase):
    code = "SS"
    name = "Start to Start"

    def __init__(self):
        super().__init__(name=self.name, code=self.code)


class StartToFinish(ConstraintTypeBase):
    code = "SF"
    name = "Start to Finish"
    
    def __init__(self):
        super().__init__(name=self.name, code=self.code)

@dataclass
class Constraint:
    task_id: str # id of the other task in the constraint relationship
    relation_type: ConstraintTypeBase # type of constraint relationship (FS, FF, SS, SF)
    lag: dt.timedelta = field(default_factory=lambda: dt.timedelta(0)) # optional lag time between the two tasks, default is 0 (no lag)