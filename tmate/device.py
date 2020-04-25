#!/usr/bin/env python3
import os
import argparse
from configparser import ConfigParser
from subprocess import Popen
from base64 import b64encode

from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen
from tornado.websocket import websocket_connect
from tornado.escape import json_decode
from tornado.httpclient import HTTPRequest


class Client(object):
    states = ['ready', 'in-queue', 'in-use', 
            'want-deprovision', 'is-deprovisioned', 
            'want-provision', 'is-provisioned']

    def __init__(self, url, profile, timeout=300):
        self.url = url
        self.timeout = timeout
        self.ioloop = IOLoop.instance()
        self.ws = None
        self.profile = profile
        self.is_provisioned = False
        self.ssh = ''
        self.web = ''
        self.web_ro = ''

        self.auth_hdr = {'Authorization': 'Basic ' + b64encode((profile['username'] + ':' + profile['password']).encode()).decode()}

        self.connect()
        PeriodicCallback(self.keep_alive, self.timeout * 1000).start()
        self.ioloop.start()

    @gen.coroutine
    def connect(self):
        print("trying to connect")
        try:
            self.ws = yield websocket_connect(HTTPRequest(url=self.url, headers=self.auth_hdr))
        except Exception:
            print("connection error")
        else:
            print("connected")
            self.run()

    @gen.coroutine
    def run(self):
        while True:
            msg = yield self.ws.read_message()
            if msg is None:
                print("connection closed")
                self.ws = None
                break
            else:
                try:
                    yield self.handle_message(msg)
                except Exception:
                    print("Error while handling message")

    def keep_alive(self):
        if self.ws is None:
            self.connect()
        else:
            self.ws.write_message("keep alive")

    def handle_message(self, message):
        #TODO make async
        data = json_decode(message)
        state = data.get("state", False)
        if not state or state not in self.states:
            return
        elif state == "want-provision":
            if not self.is_provisioned:
                # create/overwrite config file
                with open(self.profile['config_file'], 'w') as fout:
                    fout.write('[config]')

                returnCode = self.run_external(['provision.sh'])
                if returnCode != 0:
                    print("Error: provision.sh returned {}".format(returnCode))
                    self.ws.write_message({'status':'provision-failed'})
                    return
                
                connectionInfo = ConfigParser()
                connectionInfo.read(self.profile['config_file'])
                self.ssh = connectionInfo['config']['ssh']
                self.web = connectionInfo['config']['web']
                self.web_ro = connectionInfo['config']['web_ro']
                self.is_provisioned = True

            self.ws.write_message({'state':'is-provisioned','ssh':self.ssh,'web':self.web,'web_ro':self.web_ro})
        elif state == 'want-deprovision':
            if self.is_provisioned:
                returnCode = self.run_external(['deprovision.sh'])
                if returnCode != 0:
                    print("Error: deprovision.sh returned {}".format(returnCode))
                    self.ws.write_message({'status':'deprovision-failed'})
                    return
            self.ws.write_message({'status':'is-deprovisioned'})
        elif state == 'update-expiration':
            with open(self.profile['timestamp_file'], 'w') as fout:
                fout.write(str(int(data['expiration'])))

        return            


    def run_external(self, args):
        def preexec():
            os.setgid(self.profile['gid'])
            os.setuid(self.profile['uid'])
            os.chdir(self.profile['data_dir'])

        args[0] = os.path.join(self.profile['install_dir'], args[0])
        proc = Popen(args, preexec_fn=preexec)
        proc.wait()
        return proc.returncode

def get_profile(profileName):
    config = ConfigParser()
    config.read('/opt/hc-client/.config.ini')

    try:
        profile = dict(config[profileName])
    except KeyError:
        return None
    
    if not profile.get('username', False)\
        or not profile.get('password', False) \
        or not profile.get('data_dir', False)\
        or ':' in profile['username']:
        return None

    profile['data_dir'] = os.path.realpath(profile['data_dir'])
    profile['uid'] = profile.get('uid', os.getuid())
    profile['gid'] = profile.get('gid', os.getgid())
    profile['use_docker'] = profile.get('use_docker', 0)
    profile['install_dir'] = os.path.abspath(os.path.realpath(__file__) + os.path.sep + '..')
    profile['config_file'] = os.path.abspath(os.path.join(profile['data_dir'], 'config'))
    profile['timestamp_file'] = os.path.abspath(os.path.join(profile['data_dir'], 'expiration-timestamp'))

    os.makedirs(profile['data_dir'], mode=0o700, exist_ok=True)
    try:
        os.chown(profile['data_dir'], profile['uid'], profile['gid'])
    except PermissionError:
        print('Failed to chown data directory, continuing anyways...')

    os.environ['DEVICE_NAME'] = profileName
    os.environ['INSTALL_DIR'] = profile['install_dir']
    os.environ['DATA_DIR'] = profile['data_dir']
    os.environ['TMATE_SOCK'] = os.path.abspath(os.path.join(profile['data_dir'], 'tmate.sock'))
    os.environ['CONFIG_FILE'] = profile['config_file']
    os.environ['EXPIRATION_TIMESTAMP'] = profile['timestamp_file']
    os.environ['USE_DOCKER'] = str(profile['use_docker'])

    return profile


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", help="profile to use")
    args = parser.parse_args()

    profile = get_profile(args.profile)
    if profile is None:
        exit(1)

    #TODO change to wss
    client = Client("ws://localhost:8080/device/state", profile)