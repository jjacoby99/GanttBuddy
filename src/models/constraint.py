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
    task_id: str
    relation_type: ConstraintTypeBase
    lag: dt.timedelta = field(default_factory=lambda: dt.timedelta(0))
