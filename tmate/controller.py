#!/usr/bin/env python3
import os
import re
import subprocess
import configparser

import pyinotify
import requests


class New_Session_Handler(pyinotify.ProcessEvent):
    sock_re = re.compile("tmate(\d+).sock")

    def get_profiles():
        # TODO fix this function
        config = ConfigParser()
        config.read('/opt/hc-client/.config.ini')

        all_profiles = {}

        for keys in config:
            profile = config[keys]

            if not profile.get('username', False) or not profile.get('password', False) or not profile.get('data_dir', False) or ':' in profile['username']:
                continue

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

            all_profiles[key] = profile

        return all_profiles



    def my_init(self):
        self.

    def process_IN_CREATE(self, event):
        '''
        This will handle reading in the new session information and sending it back to the server
        '''
        match = self.sock_re.match(os.path.basename(event.pathname))
        if match:
            print("A new tmate socket got created!")

            # Get the ssh info
            p = subprocess.Popen(['tmate', '-S', event.pathname, 'display', '-p', r"#{tmate_ssh}"], stdout=subprocess.PIPE)
            ssh_info = p.communicate()[0].decode()

            # Get the web info
            p = subprocess.Popen(['tmate', '-S', event.pathname, 'display', '-p', r"#{tmate_web}"], stdout=subprocess.PIPE)
            web_info = p.communicate()[0].decode()

            # Get the web_ro info
            p = subprocess.Popen(['tmate', '-S', event.pathname, 'display', '-p', r"#{tmate_web_ro}"], stdout=subprocess.PIPE)
            web_ro_info = p.communicate()[0].decode()

            

            session = requests.session()
            session.post("http://localhost:5000/login", data={'name':'device$1','password':'ASubsfas2341'})
            session.post("http://localhost:5000/checkin", json={'web':'$WEB','web_ro':'$WEB_RO','ssh':'$SSH'})

