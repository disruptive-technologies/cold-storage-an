# packages
import os
import sys
import json
import time
import pprint
import requests

# project
import cold_storage.helpers as     helpers
from cold_storage.director  import Director

# Fill in from the Service Account and Project:
USERNAME   = "bsarver24te000b24bpg"       # this is the key
PASSWORD   = "8362c483e011479fb1066d9b20a0817b"     # this is the secret
PROJECT_ID = "bsarslgg7oekgsc2jb20"                # this is the project id

# set url base
API_URL_BASE = "https://api.disruptive-technologies.com/v2"


def stream(d, devices_stream_url, stream_params, n_reconnects=5):
    """Stream events for sensors in project.

    parameters:
        d                  -- Director class object.
        devices_stream_url -- Url pointing to project.
        stream_params      -- Filters used in stream.
        n_reconnects       -- Number of retries if connection lost.
    """

    # cout
    print("Listening for events... (press CTRL-C to abort)")

    # reinitialise plot
    if args['plot']:
        d.initialise_plot()
        d.plot_progress(blocking=False)

    # loop indefinetly
    nth_reconnect = 0
    while nth_reconnect < n_reconnects:
        try:
            # reset reconnect counter
            nth_reconnect = 0
    
            # get response
            response = requests.get(devices_stream_url, auth=(username,password),headers={'accept':'text/event-stream'}, stream=True, params=stream_params)
            client = sseclient.SSEClient(response)
    
            # listen for events
            print('Connected.')
            for event in client.events():
                # new data received
                event_data = json.loads(event.data)['result']['event']
    
                # serve event to director
                d.new_event_data(event_data)
    
                # plot progress
                if args['plot']:
                    d.plot_progress(blocking=False)
        
        except requests.exceptions.ConnectionError:
            nth_reconnect += 1
            print('Connection lost, reconnection attempt {}/{}'.format(nth_retry, MAX_RETRIES))
        except requests.exceptions.ChunkedEncodingError:
            nth_reconnect += 1
            print('An error occured, reconnection attempt {}/{}'.format(nth_retry, MAX_RETRIES))
        
        # wait 1s before attempting to reconnect
        time.sleep(1)


if __name__ == '__main__':

    # initialise Director instance
    d = Director(USERNAME, PASSWORD, PROJECT_ID, API_URL_BASE)

    # iterate historic events
    d.run_history()

    # stream realtime events
    d.run_stream(n_reconnects=5)

