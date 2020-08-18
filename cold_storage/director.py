# packages
import os
import sys
import time
import json
import argparse
import datetime
import requests
import sseclient
import numpy             as np
import matplotlib.pyplot as plt

# project
import cold_storage.config.styling    as stl
import cold_storage.config.parameters as params
import cold_storage.helpers           as hlp
from cold_storage.sensor              import Sensor


class Director():
    """
    Keeps track of all sensors in project.
    Spawns one Sensor object per sensors.
    When new event_data json is received, relay it to the correct object.
    """

    def __init__(self, username, password, project_id, api_url_base):
        # give to self
        self.username     = username
        self.password     = password
        self.project_id   = project_id
        self.api_url_base = api_url_base

        # parse system arguments
        self.__parse_sysargs()

        # use local file
        if self.args['path']:
            # perform some initial setups
            self.__local_setup()

            # import file as event history format
            self.event_history = hlp.import_as_event_history(self.args['path'])
        
        # use API
        else:
            # set filters for fetching data
            self.__set_filters()

            # set stream endpoint
            self.stream_endpoint = "{}/projects/{}/devices:stream".format(self.api_url_base, self.project_id)

            # fetch list of devices in project
            self.__fetch_project_devices()

            # spawn devices instances
            self.__spawn_devices()

            # fetch event history
            if self.fetch_history:
                self.__fetch_event_history()


    def __parse_sysargs(self):
        """
        Parse for command line arguments.
    
        """
    
        # create parser object
        parser = argparse.ArgumentParser(description='Cold Storage Anomaly Detectiond on Stream and Event History.')
    
        # general arguments
        now = (datetime.datetime.utcnow().replace(microsecond=0)).isoformat() + 'Z'
        parser.add_argument('--path',      metavar='', help='Absolute path to local .csv file.',                   required=False, default=None)
        parser.add_argument('--starttime', metavar='', help='Event history UTC starttime [YYYY-MM-DDTHH:MM:SSZ].', required=False, default=now)
        parser.add_argument('--endtime',   metavar='', help='Event history UTC endtime [YYYY-MM-DDTHH:MM:SSZ].',   required=False, default=now)
    
        # boolean flags
        parser.add_argument('--plot',   action='store_true', help='Plot the estimated desk occupancy.')
        parser.add_argument('--debug',  action='store_true', help='Plot algorithm operation.')
    
        # convert to dictionary
        self.args = vars(parser.parse_args())
    
        # set history flag
        if now == self.args['starttime']:
            self.fetch_history = False
        else:
            self.fetch_history = True


    def __local_setup(self):
        # verify valid path
        if not os.path.exists(self.args['path']):
            hlp.print_error('Path [{}] is not valid.'.format(self.args['path']))

        # make a fake list of devices
        self.devices = [{'name': 'local_file', 'type': 'temperature'}]

        # spawn devices
        self.__spawn_devices()


    def __set_filters(self):
        """
        Set filters for data fetched through API.

        """

        # historic events
        self.history_params = {
            'page_size': 1000,
            'start_time': self.args['starttime'],
            'end_time': self.args['endtime'],
            'event_types': ['temperature'],
        }

        # stream events
        self.stream_params = {
            'event_types': ['temperature'],
        }


    def __fetch_project_devices(self):
        """
        Fetch information about all devices in project.

        """

        # request list
        devices_list_url = "{}/projects/{}/devices".format(self.api_url_base,  self.project_id)
        device_listing = requests.get(devices_list_url, auth=(self.username, self.password))
        
        # remove fluff
        try:
            self.devices = device_listing.json()['devices']
        except KeyError as e:
            # an error here probably means connection issues
            print(e)
            hlp.print_error('Could not fetch devices.', terminate=True)


    def initialise_plot(self):
        self.hfig, self.hax = plt.subplots(len(self.sensors), 1, sharex=True)
        if len(self.sensors) < 2:
            self.hax = [self.hax]


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


    def __fetch_event_history(self):
        """
        For each sensor in project, request all events since --starttime from API.

        """

        # initialise empty event list
        self.event_history = []

        # iterate devices
        for device in self.devices:
            # isolate device identifier
            device_id = os.path.basename(device['name'])
        
            # some printing
            print('-- Getting event history for {}'.format(device_id))
        
            # initialise next page token
            self.history_params['page_token'] = None
        
            # set endpoints for event history
            event_list_url = "{}/projects/{}/devices/{}/events".format(self.api_url_base, self.project_id, device_id)
        
            # perform paging
            while self.history_params['page_token'] != '':
                event_listing = requests.get(event_list_url, auth=(self.username, self.password), params=self.history_params)
                event_json = event_listing.json()
        
                if event_listing.status_code < 300:
                    self.history_params['page_token'] = event_json['nextPageToken']
                    self.event_history += event_json['events']
                else:
                    print(event_json)
                    hlp.print_error('Status Code: {}'.format(event_listing.status_code), terminate=True)
        
                if self.history_params['page_token'] is not '':
                    print('\t-- paging')
        
        # sort event history in time
        self.event_history.sort(key=hlp.json_sort_key, reverse=False)


    def print_devices_information(self):
        """Print information about active devices in stream."""

        print('\nDirector initialised for sensors:')
        # print desks
        for sensor in self.sensors:
            print('-- {:<30}'.format(sensor))
        print()


    def run_history(self):  
        """Iterate historic event data.
    
        """

        # do nothing if no starttime is given
        if not self.fetch_history:
            return
    
        # estimate occupancy for history 
        cc = 0
        for i, event_data in enumerate(self.event_history):
            cc = hlp.loop_progress(cc, i, len(self.event_history), 25, name='event history')
            # serve event to director
            self.__new_event_data(event_data, cout=False)
    
        # initialise plot
        if self.args['plot']:
            print('\nClose the blocking plot to start stream.')
            print('A new non-blocking plot will appear for stream.')
            self.initialise_plot()
            self.plot_progress(blocking=True)
        if self.args['debug']:
            self.plot_debug()


    def run_stream(self, n_reconnects=5):
        """
        Stream events for sensors in project.
    
        Parameters
        ----------
            n_reconnects : int
        Number of retries if connection lost.

        """
    
        # cout
        print("Listening for events... (press CTRL-C to abort)")
    
        # reinitialise plot
        if self.args['plot']:
            self.initialise_plot()
            self.plot_progress(blocking=False)
    
        # loop indefinetly
        nth_reconnect = 0
        while nth_reconnect < n_reconnects:
            try:
                # reset reconnect counter
                nth_reconnect = 0
        
                # get response
                response = requests.get(self.stream_endpoint, auth=(self.username, self.password), headers={'accept':'text/event-stream'}, stream=True, params=self.stream_params)
                client = sseclient.SSEClient(response)
        
                # listen for events
                print('Connected.')
                for event in client.events():
                    # new data received
                    event_data = json.loads(event.data)['result']['event']
        
                    # serve event to director
                    self.__new_event_data(event_data)
        
                    # plot progress
                    if self.args['plot']:
                        self.plot_progress(blocking=False)
            
            except requests.exceptions.ConnectionError:
                nth_reconnect += 1
                print('Connection lost, reconnection attempt {}/{}'.format(nth_reconnect, n_reconnects))
            except requests.exceptions.ChunkedEncodingError:
                nth_reconnect += 1
                print('An error occured, reconnection attempt {}/{}'.format(nth_reconnect, n_reconnects))
            
            # wait 1s before attempting to reconnect
            time.sleep(1)


    def __new_event_data(self, event_data, cout=True):
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

        print('\nDEBUG')
        print('Close plot to see next sensor.')

        for sid in self.sensors.keys():

            sensor = self.sensors[sid]
            print(sensor.device_id)

            # reinitialise debug figure
            self.initialise_debug_plot()

            self.dax[0].plot(hlp.ux_to_dt(sensor.temperature_ux), sensor.temperature_y, color=stl.wheel[0],       label='Temperature')
            self.dax[0].plot(hlp.ux_to_dt(sensor.level_ux),       sensor.level_y,       color='k', linewidth=2.5, label='Baseline')
            self.dax[0].set_xlabel('Time')
            self.dax[0].axvline(hlp.ux_to_dt(sensor.level_ux[-1]), color='k')
            self.dax[0].axvline(hlp.ux_to_dt(sensor.level_ux[-1]+params.S_DELAY), color='k', linestyle='--', label='Median Window')
            self.dax[0].axvline(hlp.ux_to_dt(sensor.level_ux[-1]-params.S_DELAY), color='k', linestyle='--')
            self.dax[0].set_ylabel('Temperature')
            self.dax[0].legend(loc='upper left')

            self.dax[1].fill_between(hlp.ux_to_dt(sensor.upper_bound_ux), sensor.upper_bound_y, sensor.lower_bound_y, alpha=0.33, color=stl.wheel[0], label='Envelope')
            self.dax[1].plot(hlp.ux_to_dt(sensor.temperature_ux), sensor.temperature_y, color=stl.wheel[0],       label='Temperature')
            self.dax[1].plot(hlp.ux_to_dt(sensor.level_ux),       sensor.level_y,       color='k', linewidth=2.5, label='Baseline')
            self.dax[2].get_shared_x_axes().join(self.dax[1], self.dax[2])
            self.dax[2].plot(hlp.ux_to_dt(sensor.temperature_ux), np.array(sensor.temperature_y)-np.array(sensor.level_y), color=stl.wheel[0],       label='Differentiated')

            for i in range(params.N_ROBUST_IN_BOUNDS):
                t2 = sensor.level_ux[len(sensor.level_ux)-1]-params.S_ROBUST_CYCLE*(i)
                t1 = sensor.level_ux[len(sensor.level_ux)-1]-params.S_ROBUST_CYCLE*(i)-params.S_ROBUST_WIDTH
            
                yy = np.array(sensor.temperature_y) - np.array(sensor.level_y)
                xx = hlp.ux_to_dt(np.array(sensor.level_ux)[(sensor.level_ux > t1) & (sensor.level_ux < t2)])
                if len(xx) > 0:
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
        for i, sid in enumerate(self.sensors.keys()):
            self.hax[i].cla()
            sensor = self.sensors[sid]

            if len(sensor.temperature_ux) > 0:
                C = 'C{}'.format(i)
                C = stl.wheel[i%len(stl.wheel)]
                self.hax[i].plot(hlp.ux_to_dt(sensor.temperature_ux), sensor.temperature_y, color=C, label='Temperature')
                self.hax[i].plot(hlp.ux_to_dt(sensor.level_ux), sensor.level_y, '-k', linewidth=2)
                self.hax[i].fill_between(hlp.ux_to_dt(sensor.upper_bound_ux), sensor.upper_bound_y, sensor.lower_bound_y, alpha=0.5, color=C)
                self.hax[i].axvline(hlp.ux_to_dt(sensor.temperature_ux[-1] - params.S_DELAY), color='k')
                self.hax[i].legend(loc='upper right')
                self.hax[i].set_ylabel('Temperature [deg]')
        self.hax[-1].set_xlabel('Time')

        if blocking:
            plt.show()
        else:
            plt.pause(0.01)
