#!/usr/bin/env python3
import sys
from base64 import b64encode
from configparser import ConfigParser

import requests

if len(sys.argv) != 2:
    print('Usage: device.py <profile>', file=sys.stderr)
    sys.exit(1)

config = ConfigParser()
config.read('config.ini')

try:
    config = config[sys.argv[1]]
except KeyError as e:
    print('Section {} not found in config.ini'.format(e.args[0]))
    sys.exit(1)

try:
    username = config['username']
    password = config['password']
except KeyError as e:
    print('Missing required parameter {} in config.ini'.format(e.args[0]))
    sys.exit(1)

if ':' in username:
    print('Colon character (:) is not allowed inside of a username per RFC 7617', file=sys.stderr)
    sys.exit(1)

r = requests.put('http://localhost:5000/device/state', json={'state': 'client-connected'}, auth=(username, password))

sys.exit(r.status_code != 200)
