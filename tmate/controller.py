#!/usr/bin/env python3
import os
import re
import subprocess
from configparser import ConfigParser
import asyncore
from base64 import b64encode

import pyinotify
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen
from tornado.websocket import websocket_connect
from tornado.escape import json_decode, json_encode
from tornado.httpclient import HTTPRequest

ACTIVE_CLIENTS = {}


class Client(object):
    states = [
        "ready",
        "in-queue",
        "in-use",
        "want-deprovision",
        "is-deprovisioned",
        "want-provision",
        "is-provisioned",
    ]

    def __init__(self, url, timeout=300):
        self.url = url
        self.timeout = timeout
        self.ioloop = IOLoop.current()
        self.ws = None

        # self.ioloop.start()

    def auth_header(self, username, password):
        return {
            "Authorization": "Basic "
            + b64encode((username + ":" + password).encode()).decode()
        }

    async def connect(self, username, password):
        print("trying to connect")
        try:
            self.ws = await websocket_connect(
                HTTPRequest(url=self.url, headers=self.auth_header(username, password)),
                on_message_callback=self.handle_message,
            )

            PeriodicCallback(self.keep_alive, self.timeout * 1000).start()
        except Exception:
            print("connection error")
            self.ws = None

    def keep_alive(self):
        if self.ws is None:
            self.connect()
        else:
            self.ws.write_message(json_encode({"status": "keep-alive"}))

    async def handle_message(self, message):
        # TODO make async and fix
        data = json_decode(message)
        state = data.get("state", False)
        if not state or state not in self.states:
            return
        elif state == "want-provision":
            if not self.is_provisioned:
                if not self.provision():
                    print("Error: provision.sh returned {}".format(returnCode))
                    self.ws.write_message(json_encode({"status": "provision-failed"}))
                    return
            self.ws.write_message(
                json_encode(
                    {
                        "state": "is-provisioned",
                        "ssh": self.ssh,
                        "web": self.web,
                        "web_ro": self.web_ro,
                    }
                )
            )
        elif state == "want-deprovision":
            if self.is_provisioned:
                if not self.deprovision():
                    print("Error: deprovision.sh returned {}".format(returnCode))
                    self.ws.write_message(json_encode({"status": "deprovision-failed"}))
                    return
            self.ws.write_message(json_encode({"status": "is-deprovisioned"}))
        elif state == "update-expiration":
            with open(self.profile["timestamp_file"], "w") as fout:
                fout.write(str(int(data["expiration"])))

        return

    def provision(self, ssh, web, web_ro):
        pass

    def deprovision(self):
        """
        TODO: use this to kill a session
        """
        pass


class New_Session_Handler(pyinotify.ProcessEvent):
    sock_re = re.compile(r"tmate(\d+).sock")

    def my_init(self, client=None):
        """
        DO NOT OVERRIDE __init__() USE THIS FUNCTION INSTEAD
        """
        self.client = client

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


class New_Device_Handler(pyinotify.ProcessEvent):
    def my_init(self, profiles={}):
        self.profiles = profiles
        self.watch_manager = pyinotify.WatchManager()

    def process_IN_CREATE(self, event):
        register_device(event.pathname, self.profiles, self.watch_manager)


def get_profiles():
    config = ConfigParser()
    config.read("/opt/hc-client/.config.ini")

    all_profiles = {}

    for key in config:
        profile = config[key]

        if not profile.get("username", False) or not profile.get("password", False):
            continue

        settings = {
            "username": profile["username"],
            "password": profile["password"],
        }

        all_profiles[key] = settings
    return all_profiles


def register_device(path, profiles, watch_manager):
    device_re = re.compile(r"^(device\d+)$")
    matches = device_re.match(path)
    if matches:
        profile_name = matches.group(1)

        clientProfile = profiles.get(profile_name, False)
        if clientProfile:

            newClient = Client("wss://virtual.carhackingvillage.com")
            newClient.connect(clientProfile["username"], clientProfile["password"])

            ACTIVE_CLIENTS[profile_name] = newClient
            # TODO do we need event_notifier
            event_notifier = pyinotify.TornadoAsyncNotifier(
                watch_manager, IOLoop.current(), New_Session_Handler(newClient)
            )

            watch_manager.add_watch(path, pyinotify.IN_CREATE)


def main():
    if not os.path.exists("/tmp/devices"):
        os.mkdir("/tmp/devices")

    profiles = get_profiles()

    # Create the watcher loop
    watch_manager = pyinotify.WatchManager()

    device_handler = New_Device_Handler(profiles)

    # TODO do we need event_notifier?
    event_notifier = pyinotify.TornadoAsyncNotifier(
        watch_manager, IOLoop.current(), device_handler
    )

    for files in os.listdir("/tmp/devices"):
        if os.path.isdir(files):
            register_device(files, profiles, device_handler.watch_manager)

    IOLoop.current().start()
    event_notifier.stop()


if __name__ == "__main__":
    main()