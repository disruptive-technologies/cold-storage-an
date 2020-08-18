# packages
import sys
import argparse
import datetime
import numpy  as np
import pandas as pd


def convert_event_data_timestamp(ts):
    """
    Convert the default event_data timestamp format to Pandas and unixtime format.

    Parameters
    ----------
    ts : str 
        API event_data timestamp format.

    Returns
    -------
    timestamp : datetime 
        Pandas Timestamp object format.
    unixtime : int 
        Integer number of seconds since 1 January 1970.

    """

    timestamp = pd.to_datetime(ts)
    unixtime  = pd.to_datetime(np.array([ts])).astype(int)[0] // 10**9

    return timestamp, unixtime


def ux_to_dt(ux):
    """
    Convert unixtime to datetime format.

    Parameters
    ----------
    ux : int 
        Seconds since 01-01-1970.

    returns:
    dt : datetime 
        Pandas datetime format.

    """

    # create datetime
    dt = pd.to_datetime(ux, unit='s')

    return dt

    
def print_error(text, terminate=True):
    """
    Print an error to console.
    
    Parameters
    ----------
    text : str 
        String to be printed with error.
    terminate : bool 
        Terminates execution if True.

    """

    print('ERROR: {}'.format(text))
    if terminate:
        sys.exit()


def loop_progress(i_track, i, n_max, n_steps, name=None, acronym=' '):
    """
    Print progress to console

    Parameters
    ----------
    i_track : int 
        Progress tracker.
        Tracks relative progress in loop and must therefore be returned.
    i : int 
        Current loop index.
    n_max : int 
        Loop end value.
    n_steps : int 
        Number of steps printed in loop.

    """

    # number of indices in each progress element
    part = n_max / n_steps

    if i_track == 0:
        # print empty bar
        print('    |')
        if name is None:
            print('    └── Progress:')
        else:
            print('    └── {}:'.format(name))
        print('        ├── [ ' + (n_steps-1)*'-' + ' ] ' + acronym)
        i_track = 1
    elif i > i_track + part:
        # update tracker
        i_track = i_track + part

        # print bar
        print('        ├── [ ' + int(i_track/part)*'#' + (n_steps - int(i_track/part) - 1)*'-' + ' ] ' + acronym)

    # return tracker
    return i_track


def dt_timestamp_format(tx):
    """
    Convert datetime object to DT timestamp format.

    Parameters
    ----------
    tx : datetime 
        Pandas datetime object.

    Returns
    -------
    dtt : str 
        API timestamp format.

    """

    year   = '{:04}'.format(tx.year)
    month  = '{:02}'.format(tx.month)
    day    = '{:02}'.format(tx.day)
    hour   = '{:02}'.format(tx.hour)
    minute = '{:02}'.format(tx.minute)
    second = '{:02}'.format(tx.second)

    dtt = year + '-' + month + '-' + day + 'T' + hour + ':' + minute + ':' + second + 'Z'
    return dtt


def api_json_format(timestamp, temperature):
    """
    Create an event that imitates API json format.

    Parameters
    ----------
    timestamp : str
        Event UTC timestamp in API format.
    temperature : float 
        Event temperature value.

    Returns
    -------
    json : dict 
        API json format.

    """

    json = {
        'targetName': 'local_file',
        'data': {
            'temperature': {
                'value':      temperature,
                'updateTime': timestamp,
            }
        }
    }

    return json


def import_as_event_history(path):
    """
    Import file as event history json format.

    Parameters
    ----------
    path : str 
        Absolute path to file.

    Returns
    -------
    events : list 
        List of historic event jsons.

    """

    # initialise output list
    events = []

    # import through pandas dataframe
    df = pd.read_csv(path)

    # verify columns existance
    if not 'temperature' in df.columns or not 'unix_time' in df.columns:
        print_error('Imported file should have columns \'temperature\' and \'unix_time\'.')

    # extract UTC timestamps
    tx = pd.to_datetime(df['unix_time'], unit='s')

    # iterate events
    for i in range(len(df)):
        # convert unixtime to DT format
        timestamp = dt_timestamp_format(tx[i])

        # create event json format
        json = api_json_format(timestamp, df['temperature'].iloc[i])

        # append output
        events.append(json)

    return events


def json_sort_key(json):
    """
    Return the event update time converted to unixtime.

    Parameters
    json : dict 
        Event data json.

    Returns
    -------
    unixtime : int 
        Seconds since 01-01-1970.

    """

    timestamp = json['data']['temperature']['updateTime']
    _, unixtime = convert_event_data_timestamp(timestamp)
    return unixtime
