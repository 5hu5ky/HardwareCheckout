#!/usr/bin/env python3
import os, sys
from base64 import b64encode

from socketio import Client

username = os.environ['DEVICENAME'].encode('latin1')
password = os.environ['PASSWORD'].encode('latin1')
data_dir = os.environ['DEVICE_DIR']
dirfd = os.open(data_dir, os.O_PATH)
auth_hdr = {'Authorization': 'Basic ' + b64encode(username + b':' + password).decode('latin1')}

c = Client()

initial_connect = False
is_provisioned = False
error = 1


def openat(*args, **kwargs):
    def opener(path, flags):
        return os.open(path, flags, dir_fd=dirfd)
    return open(*args, opener=opener, **kwargs)


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
    if 'state' not in data:
        return
    if data['state'] == 'want-provision':
        print('Server wants a provision')
        if not is_provisioned:
            print('Provisioning...')
            code = os.system('./provision.sh')
            if code:
                print('ERROR: provision.sh failed with exit code %d' % code, file=sys.stderr)
                send('provision-failed')
                return
            is_provisioned = True
        else:
            print('Already provisioned, nothing to do')
        send('is-provisioned')
    elif data['state'] == 'want-deprovision':
        print('Server wants a deprovision')
        if is_provisioned:
            print('Deprovisioning...')
            code = os.system('./deprovision.sh')
            if code:
                print('ERROR: deprovision.sh failed with exit code %d' % code, file=sys.stderr)
                send('deprovision-failed')
                return
            is_provisioned = False
        else:
            print('Already deprovisioned, nothing to do')
        send('is-deprovisioned')
    elif data['state'] == 'update-expiration':
        print('Updating expiration timestamp')
        with openat('expiration-timestamp', 'w') as f:
            f.write(str(int(data['expiration'])))


def send(state):
    data = {'state': state}
    print('Sending %r to server' % data)
    c.send({'state': state}, namespace='/device')


c.connect('http://localhost:5000', headers=auth_hdr)
c.wait()
sys.exit(error)
