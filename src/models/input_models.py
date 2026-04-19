from dataclasses import dataclass
import datetime as dt

from typing import Optional

@dataclass
class FeedHeadInputs:
    n_liner_strip: int = 24
    n_filler_strip: int = 36
    n_grates_strip: int = 15

    t_liner_strip: int = 10
    t_filler_strip: int = 10
    t_grates_strip: int = 10

    t_liner_install: int = 10
    t_filler_install: int = 10
    t_grates_install: int = 10

    # only if n_install != n_strip
    n_liner_install: Optional[int] = None 
    n_filler_install: Optional[int] = None
    n_grates_install: Optional[int] = None

@dataclass
class ShellInputs:
    n_rows_strip: int = 30
    modules_per_row_strip: int = 2

    t_row_strip: int = 10

    n_rows_install: Optional[int] = None
    modules_per_row_install: Optional[int] = None

    t_row_install: int = 10


@dataclass 
class DischargeInputs:
    n_grates_strip: int = 18
    n_pulps_strip: int = 19

    replace_dc: bool = True

    t_grate_strip: int = 10
    t_pulp_strip: int = 10

    t_remove_dc: Optional[int] = None

    n_grates_install: Optional[int] = None
    n_pulps_install: Optional[int] = None

    t_grate_install: int = 10
    t_pulp_install: int = 10

    t_install_dc: Optional[int] = None

@dataclass
class RelineScope:
    start_date: dt.datetime
    feed_end: FeedHeadInputs
    shell: ShellInputs
    discharge: DischargeInputs

    # Inching
    t_inch: int = 10 # inch time in minutes

    