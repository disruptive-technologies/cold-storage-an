# packages
import sys
import numpy             as np
import matplotlib.pyplot as plt

# project
import cold_storage.helpers           as helpers
import cold_storage.config.styling    as stl
import cold_storage.config.parameters as params


class Sensor():
    """
    One Sensor object for each sensor in project.
    It keeps track of the algorithm state between events.
    When new event_data json is received, iterate algorithm one sample.
    """

    def __init__(self, device, device_id, args):
        # give to self
        self.device    = device
        self.device_id = device_id
        self.args      = args

        # containers
        self.temperature_ux = [] # temperature unixtime
        self.temperature_y  = [] # temperature values
        self.level_ux       = [] # level unixtime
        self.level_y        = [] # level values
        self.minval_ux      = [] # minimum temperature unixtime
        self.minval_y       = [] # minimum temperature value
        self.maxval_ux      = [] # maximum temperature unixtime
        self.maxval_y       = [] # maximum temperature value
        self.mad_ux         = [] # median absolute deviation unixtime
        self.mad_y          = [] # median absolute deviation value
        self.upper_bound_ux = [] # upper bound unixtime
        self.upper_bound_y  = [] # upper bound value
        self.lower_bound_ux = [] # lower bound unixtime
        self.lower_bound_y  = [] # lower bound value

        # variables
        self.n_samples    = 0 # number of event samples received
        self.robust_cycle = 0 # samples since last robust cycle trigger


    def new_event_data(self, event_data):
        """Receive new event from Director and iterate algorithm.

        parameters:
            event_data -- Event json containing temperature data.
        """

        # convert timestamp to unixtime
        _, unixtime = helpers.convert_event_data_timestamp(event_data['data']['temperature']['updateTime'])

        # append self
        self.temperature_ux.append(unixtime)
        self.temperature_y.append(event_data['data']['temperature']['value'])
        self.n_samples += 1

        # iterate algorithm
        self.iterate()


    def iterate(self):
        """Iterate algorithm for new event data."""

        # calculate level as median of delay window
        delay_window = np.array(self.temperature_y)[self.temperature_ux > self.temperature_ux[-1] - 2*params.S_DELAY]
        if len(delay_window) > 0:
            # append level
            self.level_ux.append(self.temperature_ux[-1] - params.S_DELAY)
            self.level_y.append(np.median(delay_window))

        # robust sampling back in time
        if self.temperature_ux[-1] - self.robust_cycle > params.S_ROBUST_CYCLE:
            self.robust_sampling()

        # calculate bounds
        n_bounds = min(len(self.mad_y), params.N_ROBUST_IN_BOUNDS)
        if n_bounds > 0:
            # calculate bounds
            upper_value = max(params.BOUND_MINVAL, np.median(np.array(self.maxval_y[-n_bounds:])) + np.median(np.array(self.mad_y[-n_bounds:]))*params.MMAD)
            lower_value = min(-params.BOUND_MINVAL, np.median(np.array(self.minval_y[-n_bounds:])) - np.median(np.array(self.mad_y[-n_bounds:]))*params.MMAD)

            # add level to bound
            upper_value = self.level_y[-1] + upper_value
            lower_value = self.level_y[-1] + lower_value

            # append calculated bounds
            self.upper_bound_ux.append(self.temperature_ux[-1] - params.S_DELAY)
            self.upper_bound_y.append(upper_value)
            self.lower_bound_ux.append(self.temperature_ux[-1] - params.S_DELAY)
            self.lower_bound_y.append(lower_value)
        else:
            # just pad with temperature values
            self.upper_bound_ux.append(self.temperature_ux[-1] - params.S_DELAY)
            self.upper_bound_y.append(self.temperature_y[-1])
            self.lower_bound_ux.append(self.temperature_ux[-1] - params.S_DELAY)
            self.lower_bound_y.append(self.temperature_y[-1])


    def robust_sampling(self):
        """Find maxval, minval and MAD for historic data window."""

        # isolate robust window
        t1 = self.temperature_ux[-1] - params.S_DELAY - params.S_ROBUST_WIDTH
        t2 = self.temperature_ux[-1] - params.S_DELAY
        robust_window = np.array(self.temperature_y)[(self.temperature_ux >= t1) & (self.temperature_ux <= t2)]
        robust_level  = np.array(self.level_y)[(self.temperature_ux >= t1) & (self.temperature_ux <= t2)]
        
        if len(robust_window) > 0:
            # calculate min and max of delayed window
            self.minval_ux.append(self.temperature_ux[-1] - params.S_DELAY)
            self.maxval_ux.append(self.temperature_ux[-1] - params.S_DELAY)
            self.maxval_y.append(max(robust_window - robust_level))
            self.minval_y.append(min(robust_window - robust_level))
        
            # calculate mad
            self.mad_ux.append(self.temperature_ux[-1] - params.S_DELAY)
            yy = robust_window - robust_level
            self.mad_y.append(np.median(abs(yy - np.median(yy))))
        
        # update cycle tracker
        self.robust_cycle = self.temperature_ux[-1]
