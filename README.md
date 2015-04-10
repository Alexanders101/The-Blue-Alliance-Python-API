# The-Blue-Alliance-Python-API
Python Numpy based bindings for the [TheBlueAlliance.com](TheBlueAlliance.com) api v2. It works on both Python 2 and 3,
and is compatible with every operating system.

## Requirements
- Python 2.x or 3.x
- Numpy
- Joblib

## Install Instructions:
1. `sudo pip (or pip3) install TheBlueAlliance`

Example Usage:

  ```
  from TheBlueAlliance import *
  
  event_code = get_events_and_codes(2015, 'Silicon Valley')[1]
  event = Event('github_user', 'test', '1.0', event_code)
  
  event.get_event_info()
  ```

## Build instructions (Linux)
1. `sudo pip (or pip3) install -r requirements.txt`
2. `python (or python3) setup.py build`
3. `sudo python (or python3) setup.py install`




