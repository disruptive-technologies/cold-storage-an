
# delay
H_DELAY = 3                 # hours of historic data used in thresholds (rolling median halfwidth)
S_DELAY = 60*60*H_DELAY     # seconds of historic data used in thresholds

# robust sampling
S_ROBUST_CYCLE     = 60*60*16   # period length for robust statistics calculation in seconds
S_ROBUST_WIDTH     = 60*60*24   # window width for robust statistics calculation in seconds
N_ROBUST_DAYS      = 5          # number of days back in time used for robust statistics calculation

# bounds / threshold
N_ROBUST_IN_BOUNDS = int(((60*60*24) / S_ROBUST_CYCLE) * N_ROBUST_DAYS)     # number of robust windows when calculating bounds
MMAD = 1                                                                    # mad modifier
BOUND_MINVAL = 0                                                            # minimum value allowed in bounds
STORAGE_MAXTEMP = 4                                                         # critical temperature

