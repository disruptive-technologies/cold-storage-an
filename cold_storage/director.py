# packages
import os
import sys
import numpy             as np
import matplotlib.pyplot as plt

# project
import cold_storage.config.styling    as stl
import cold_storage.config.parameters as params
import cold_storage.helpers           as helpers
from cold_storage.sensor              import Sensor


class Director():
    """
    Keeps track of all sensors in project.
    Spawns one Sensor object per sensors.
    When new event_data json is received, relay it to the correct object.
    """

    def __init__(self, devices, args):
        # add to self
        self.args    = args
        self.devices = devices

        # initialise Desk and Reference objects from devices
        self.__spawn_devices()

        # print some information
        self.print_devices_information()

        # initialise plot
        if self.args['plot']:
            self.initialise_plot()


    def initialise_plot(self):
        self.hfig, self.hax = plt.subplots(len(self.sensors), 1, sharex=True)


    def initialise_debug_plot(self):
        self.dfig, self.dax = plt.subplots(3, 1)


    def __spawn_devices(self):
        """Use list of devices to spawn Desk and Reference objects for each."""

        # empty lists of devices
        self.sensors = {}

        # iterate list of devices
        for device in self.devices:
            # verify temperature type
            if device['type'] == 'temperature':
                # get device id
                device_id = os.path.basename(device['name'])

                # new key in sensor dictionary
                self.sensors[device_id] = Sensor(device, device_id, self.args)


    def print_devices_information(self):
        """Print information about active devices in stream."""

        print('\nDirector initialised for sensors:')
        # print desks
        for sensor in self.sensors:
            print('-- {:<30}'.format(sensor))
        print()


    def new_event_data(self, event_data, cout=True):
        """Receive new event_data json and pass it along to the correct device object.

        Parameters:
            event_data -- Data json containing new event data.
            cout       -- Print device information to console if True.
        """

        # get id of source sensor
        source_id = os.path.basename(event_data['targetName'])

        # verify temperature event
        if 'temperature' in event_data['data'].keys():
            # check if source device is known
            if source_id in self.sensors.keys():
                # serve event to desk
                self.sensors[source_id].new_event_data(event_data)
                if cout: print('-- {:<30}'.format(source_id))


    def plot_debug(self):
        for sid in self.sensors.keys():
            sensor = self.sensors[sid]
            print(sensor.device_id)
            # reinitialise debug figure
            self.initialise_debug_plot()

            self.dax[0].plot(helpers.unixtime_to_datetime(sensor.temperature_ux), sensor.temperature_y, color=stl.wheel[0],       label='Temperature')
            self.dax[0].plot(helpers.unixtime_to_datetime(sensor.level_ux),       sensor.level_y,       color='k', linewidth=2.5, label='Baseline')
            self.dax[0].set_xlabel('Time')
            self.dax[0].axvline(helpers.unixtime_to_datetime(sensor.level_ux[-1]), color='k')
            self.dax[0].axvline(helpers.unixtime_to_datetime(sensor.level_ux[-1]+params.S_DELAY), color='k', linestyle='--', label='Median Window')
            self.dax[0].axvline(helpers.unixtime_to_datetime(sensor.level_ux[-1]-params.S_DELAY), color='k', linestyle='--')
            self.dax[0].set_ylabel('Temperature')
            self.dax[0].legend(loc='upper left')

            self.dax[1].fill_between(helpers.unixtime_to_datetime(sensor.upper_bound_ux), sensor.upper_bound_y, sensor.lower_bound_y, alpha=0.33, color=stl.wheel[0], label='Envelope')
            self.dax[1].plot(helpers.unixtime_to_datetime(sensor.temperature_ux), sensor.temperature_y, color=stl.wheel[0],       label='Temperature')
            self.dax[1].plot(helpers.unixtime_to_datetime(sensor.level_ux),       sensor.level_y,       color='k', linewidth=2.5, label='Baseline')
            self.dax[2].get_shared_x_axes().join(self.dax[1], self.dax[2])
            self.dax[2].plot(helpers.unixtime_to_datetime(sensor.temperature_ux), np.array(sensor.temperature_y)-np.array(sensor.level_y), color=stl.wheel[0],       label='Differentiated')
            for i in range(params.N_ROBUST_IN_BOUNDS):
                t2 = sensor.level_ux[len(sensor.level_ux)-1]-params.S_ROBUST_CYCLE*(i)
                t1 = sensor.level_ux[len(sensor.level_ux)-1]-params.S_ROBUST_CYCLE*(i)-params.S_ROBUST_WIDTH
            
                yy = np.array(sensor.temperature_y) - np.array(sensor.level_y)
                xx = helpers.unixtime_to_datetime(np.array(sensor.level_ux)[(sensor.level_ux > t1) & (sensor.level_ux < t2)])
                maxval = np.ones(len(xx))*max(yy[(sensor.level_ux > t1) & (sensor.level_ux < t2)])
                lx = [xx[0], xx[0]]
                ly = [maxval[0]-0.5, maxval[0]+0.5]
                rx = [xx[-1], xx[-1]]
                ry = [maxval[0]-0.5, maxval[0]+0.5]
                self.dax[2].plot(xx, maxval, color=stl.wheel[1])
                self.dax[2].plot(lx, ly, color=stl.wheel[1], linewidth=2)
                self.dax[2].plot(rx, ry, color=stl.wheel[1], linewidth=2)
            
                minval = np.ones(len(xx))*min(yy[(sensor.level_ux > t1) & (sensor.level_ux < t2)])
                lx = [xx[0], xx[0]]
                ly = [minval[0]-0.5, minval[0]+0.5]
                rx = [xx[-1], xx[-1]]
                ry = [minval[0]-0.5, minval[0]+0.5]
                self.dax[2].plot(xx, minval, color=stl.wheel[1])
                self.dax[2].plot(lx, ly, color=stl.wheel[1], linewidth=2)
                self.dax[2].plot(rx, ry, color=stl.wheel[1], linewidth=2)
            self.dax[2].plot(rx, ry, color=stl.wheel[1], linewidth=2, label='Window Extrema')
            
            self.dax[1].set_xlabel('Time')
            self.dax[1].set_ylabel('Temperature')
            self.dax[1].legend(loc='upper left')
            self.dax[2].set_xlabel('Time')
            self.dax[2].set_ylabel('Temperature')
            self.dax[2].legend(loc='upper left')
        
        plt.show()


    def plot_progress(self, blocking):
        # iterate sensors
        if len(self.sensors) > 1:
            for i, sid in enumerate(self.sensors.keys()):
                self.hax[i].cla()
                sensor = self.sensors[sid]
                C = 'C{}'.format(i)
                C = stl.wheel[i%len(stl.wheel)]
                self.hax[i].plot(helpers.unixtime_to_datetime(sensor.temperature_ux), sensor.temperature_y, color=C, label='Temperature')
                self.hax[i].plot(helpers.unixtime_to_datetime(sensor.level_ux), sensor.level_y, '-k', linewidth=2)
                self.hax[i].fill_between(helpers.unixtime_to_datetime(sensor.upper_bound_ux), sensor.upper_bound_y, sensor.lower_bound_y, alpha=0.5, color=C)
                self.hax[i].axvline(helpers.unixtime_to_datetime(sensor.temperature_ux[-1] - params.S_DELAY), color='k')
                self.hax[i].legend(loc='upper right')
                self.hax[i].set_ylabel('Temperature [deg]')
            self.hax[-1].set_xlabel('Time')
        else:
            for sid in self.sensors.keys():
                self.hax.cla()
                sensor = self.sensors[sid]
                self.hax.fill_between(helpers.unixtime_to_datetime(sensor.upper_bound_ux), sensor.upper_bound_y, sensor.lower_bound_y, where=(np.array(sensor.level_y) < params.STORAGE_MAXTEMP), alpha=0.33, color=stl.wheel[0], label='Bounds')
                self.hax.fill_between(helpers.unixtime_to_datetime(sensor.upper_bound_ux), 0, 1, where=(np.array(sensor.level_y) > params.STORAGE_MAXTEMP), alpha=0.5, color=stl.wheel[1], label='Alert', transform=self.hax.get_xaxis_transform())
                self.hax.plot(helpers.unixtime_to_datetime(sensor.temperature_ux), sensor.temperature_y, color=stl.wheel[0], label='Temperature')
                self.hax.plot(helpers.unixtime_to_datetime(sensor.level_ux), sensor.level_y, '-', color='k', linewidth=2.5, label='Baseline')
                self.hax.axvline(helpers.unixtime_to_datetime(sensor.temperature_ux[-1] - params.S_DELAY), color=stl.wheel[2])
                self.hax.legend(loc='upper left')
                self.hax.set_ylabel('Temperature [deg]')
                self.hax.set_xlabel('Time')

        if blocking:
            plt.show()
        else:
            plt.pause(0.01)
