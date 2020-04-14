#!/usr/bin/env python3
import os, os.path, sys
from base64 import b64encode
from configparser import ConfigParser
from subprocess import Popen

from socketio import Client

if len(sys.argv) != 2:
    print('Usage: device.py <profile>', file=sys.stderr)
    sys.exit(1)

config = ConfigParser()
config.read('/opt/hc-client/.config.ini')

try:
    config = config[sys.argv[1]]
except KeyError as e:
    print('Section {} not found in config.ini'.format(e.args[0]))
    sys.exit(1)

try:
    username = config['username']
    password = config['password']
    data_dir = os.path.realpath(config['data_dir'])
except KeyError as e:
    print('Missing required parameter {} in config.ini'.format(e.args[0]))
    sys.exit(1)

if ':' in username:
    print('Colon character (:) is not allowed inside of a username per RFC 7617', file=sys.stderr)
    sys.exit(1)

try:
    uid = config['uid']
except KeyError:
    uid = os.getuid()

try:
    gid = config['gid']
except KeyError:
    gid = os.getgid()

try:
    use_docker = config['use_docker']
except KeyError:
    use_docker = 0

install_dir = os.path.abspath(os.path.realpath(sys.argv[0]) + os.path.sep + '..')
os.makedirs(data_dir, mode=0o700, exist_ok=True)

try:
    os.chown(data_dir, uid, gid)
except PermissionError:
    print('Failed to chown data directory, continuing anyways...')

os.environ['DEVICE_NAME'] = sys.argv[1]
os.environ['INSTALL_DIR'] = install_dir
os.environ['DATA_DIR'] = data_dir
os.environ['TMATE_SOCK'] = os.path.abspath(data_dir + os.path.sep + 'tmate.sock')
os.environ['CONFIG_FILE'] = os.path.abspath(data_dir + os.path.sep + 'config')
os.environ['EXPIRATION_TIMESTAMP'] = os.path.abspath(data_dir + os.path.sep + 'expiration-timestamp')
os.environ['USE_DOCKER'] = str(use_docker)

auth_hdr = {'Authorization': 'Basic ' + b64encode((username + ':' + password).encode()).decode()}

c = Client()

initial_connect = False
is_provisioned = False
error = 1

ssh = ''
web = ''
web_ro = ''


def run_external(args):
    def preexec():
        os.setgid(gid)
        os.setuid(uid)
        os.chdir(data_dir)

    args[0] = install_dir + os.path.sep + args[0]
    proc = Popen(args, preexec_fn=preexec)
    proc.wait()
    return proc.returncode


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
    global ssh, web, web_ro
    print('Received data from server: %r' % data)
    if 'state' not in data:
        return
    if data['state'] == 'want-provision':
        print('Server wants a provision')
        if not is_provisioned:
            with open(os.environ['CONFIG_FILE'], 'w') as f:
                print('[config]', file=f)
            print('Provisioning...')
            code = run_external(['provision.sh'])
            if code:
                print('ERROR: provision.sh failed with exit code %d' % code, file=sys.stderr)
                send('provision-failed')
                return
            config = ConfigParser()
            config.read(os.environ['CONFIG_FILE'])
            ssh = config['config']['ssh']
            web = config['config']['web']
            web_ro = config['config']['web_ro']
            is_provisioned = True
        else:
            print('Already provisioned, nothing to do')
        send('is-provisioned', ssh=ssh, web=web, web_ro=web_ro)
    elif data['state'] == 'want-deprovision':
        print('Server wants a deprovision')
        if is_provisioned:
            print('Deprovisioning...')
            code = run_external(['deprovision.sh'])
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
        with open(os.environ['EXPIRATION_TIMESTAMP'], 'w') as f:
            f.write(str(int(data['expiration'])))


def send(state, **kwargs):
    kwargs['state'] = state
    print('Sending %r to server' % kwargs)
    c.send(kwargs, namespace='/device')


c.connect('https://localhost:5000', headers=auth_hdr)
c.wait()
sys.exit(error)
