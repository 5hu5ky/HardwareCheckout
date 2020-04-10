#!/usr/bin/env python3
import os, sys
from base64 import b64encode

from socketio import Client

username = os.environ['DEVICENAME'].encode('latin1')
password = os.environ['PASSWORD'].encode('latin1')
auth_hdr = {'Authorization': 'Basic ' + b64encode(username + b':' + password).decode('latin1')}

c = Client()

initial_connect = False
is_provisioned = False
error = 1


@c.on('connect', namespace='/device')
def device_connected():
    global initial_connect
    initial_connect = True
    print('Device connected to server')


@c.on('disconnect', namespace='/device')
def device_disconnected():
    if not initial_connect:
        print('FATAL ERROR: Server rejected connection', file=sys.stderr)
        print('Verify that the DEVICENAME and PASSWORD environment variables are correct and try again', file=sys.stderr)
        c.disconnect()
    else:
        print('Device disconnected, should reconnect soon')
        print('If not, try CTRL-c and verify DEVICENAME and PASSWORD environment variables')


@c.on('json', namespace='/device')
def handle_response(data):
    global is_provisioned, error
    print('Received data from server: %r' % data)
    if 'state' not in data or data[state] not in ('want-provision', 'want-deprovision'):
        return
    if data[state] == 'want-provision':
        if not is_provisioned:
            # provision here
            code = os.system('./provision.sh')
            if code:
                print('ERROR: provision.sh failed with exit code %d' % code, file=sys.stderr)
                c.send({'state': 'provision-failed'})
                return
            is_provisioned = True
        c.send({'state': 'is-provisioned'}, namespace='/device')
    elif data[state] == 'want-deprovision':
        if is_provisioned:
            code = os.system('./deprovision.sh')
            if code:
                print('ERROR: deprovision.sh failed with exit code %d' % code, file=sys.stderr)
                c.send({'state': 'deprovision-failed'})
                return
            is_provisioned = False
        c.send({'state': 'is-deprovisioned'}, namespace='/device')


c.connect('http://localhost:5000', headers=auth_hdr)
c.wait()
sys.exit(error)
