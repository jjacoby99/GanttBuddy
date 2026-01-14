from dataclasses import dataclass
import datetime as dt

@dataclass
class RelineScope:
    start_date: dt.datetime

    # Inching
    t_inch: int = 10 # inch time in minutes

    # Feed end
    feed_head_segments: int = 24
    t_fh: int = 10 # feed head removal time in minutes
    feed_head_fillers: int = 36
    t_fh_filler: int = 10 # fh filler removal time in minutes
    feed_head_grates: int = 15
    t_fh_grates: int = 10 # fh grates removal time in minutes

    # Shell
    shell_rows: int = 30
    modules_per_shell_row: int = 2
    t_shell_row: int = 30 # shell row removal time in minutes

    # Discharge end 
    discharge_grate_rows: int = 18 
    t_discharge_grate_row: int = 30 # time in minutes
    pulp_lifter_rows: int = 19 # check 
    t_pulp_lifter_row: int = 30 #  time in minutes
    replace_discharge_cone: bool = True
    t_discharge_cone: int = 4*60
