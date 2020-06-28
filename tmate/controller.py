#!/usr/bin/env python3
import os
import re
import subprocess
from configparser import ConfigParser

import pyinotify


class New_Session_Handler(pyinotify.ProcessEvent):
    sock_re = re.compile(r"tmate(\d+).sock")

    def get_profiles(self):
        # TODO fix this function
        config = ConfigParser()
        config.read("/opt/hc-client/.config.ini")

        self.all_profiles = {}

        for key in config:
            profile = config[key]

            if not profile.get("username", False) or not profile.get("password", False):
                continue

            settings = {
                "username": profile['username'],
                "password": profile['password']
            }

            self.all_profiles[key] = settings


    def my_init(self):
        self.get_profiles()

    def process_IN_CREATE(self, event):
        """
        This will handle reading in the new session information and sending it back to the server
        """
        match = self.sock_re.match(os.path.basename(event.pathname))
        if match:
            print("A new tmate socket got created!")

            # Get the ssh info
            p = subprocess.Popen(
                ["tmate", "-S", event.pathname, "display", "-p", r"#{tmate_ssh}"],
                stdout=subprocess.PIPE,
            )
            ssh_info = p.communicate()[0].decode()

            # Get the web info
            p = subprocess.Popen(
                ["tmate", "-S", event.pathname, "display", "-p", r"#{tmate_web}"],
                stdout=subprocess.PIPE,
            )
            web_info = p.communicate()[0].decode()

            # Get the web_ro info
            p = subprocess.Popen(
                ["tmate", "-S", event.pathname, "display", "-p", r"#{tmate_web_ro}"],
                stdout=subprocess.PIPE,
            )
            web_ro_info = p.communicate()[0].decode()

            # TODO: Connect and talk to the server

