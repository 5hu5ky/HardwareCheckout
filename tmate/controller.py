#!/usr/bin/env python3
import os
import re
from configparser import ConfigParser
import asyncore
from base64 import b64encode

import pyinotify
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado import gen
from tornado.websocket import websocket_connect
from tornado.escape import json_decode, json_encode
from tornado.httpclient import HTTPRequest
from tornado.process import Subprocess as subprocess

ACTIVE_CLIENTS = {}
device_re = re.compile(r"^.*(device\d+)$")

class Client(object):
    devices = {}

    def __init__(self, url, username, password, timeout = 300):
        self.url = url
        self.username = username
        self.password = password
        self.timeout = timeout

    def auth_header(self, username, password):
        return {
            "Authorization": "Basic "
            + b64encode((username + ":" + password).encode()).decode()
        }

    async def connect(self):
        print("trying to connect")
        try:
            self.ws = await websocket_connect(
                HTTPRequest(url=self.url, headers=self.auth_header(self.username, self.password)),
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
            print("Keep Alive")
            self.ws.write_message(json_encode({"type": "keep-alive"}))

    async def handle_message(self, message):
        # TODO make async and fix
        try:
            data = json_decode(message)
            msg_type = data.get("type", None)
            params = data.get("params", None)
        except Exception:
            return

        if not msg_type:
            return
        elif msg_type == 'restart':
            print("Got restart request for {}".format(params))
            # TODO find this device and send it a studown command
            await self.deprovision(params)


    async def deprovision(self, device):
        p = subprocess(
            ["tmate", "-S", os.path.join("/tmp/devices/", device, "{}.sock".format(device)), "wait", "tmate-ready"], 
            stdout = subprocess.STREAM, 
            stderr = subprocess.STREAM
            )

        try:
            await p.wait_for_exit()
        except Exception:
            return False
        return True

class New_Device_Handler(pyinotify.ProcessEvent):
    def my_init(self, profiles={}):
        self.profiles = profiles

    def process_IN_CREATE(self, event):
        print("New Device Created")
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


async def register_device(path, profiles):
    matches = device_re.match(path)
    if matches:
        profile_name = matches.group(1)

        clientProfile = profiles.get(profile_name, False)
        if clientProfile:
            print("Registering new Client: {}".format(profile_name))
            


async def main():
    if not os.path.exists("/tmp/devices"):
        os.mkdir("/tmp/devices")

    profiles = get_profiles()

    newClient = Client("wss://virtual.carhackingvillage.com", profiles['controller']["username"], profiles['controller']["password"])
    await newClient.connect()

    # Create the watch manager
    watch_manager = pyinotify.WatchManager()

    # TODO do we need event_notifier?
    event_notifier = pyinotify.TornadoAsyncNotifier(
        watch_manager, IOLoop.current(), New_Device_Handler(profiles=profiles)
    )
    watch_manager.add_watch("/tmp/devices", pyinotify.IN_CREATE)

    for files in os.listdir("/tmp/devices"):
        full_path = os.path.join("/tmp/devices", files)
        if os.path.isdir(full_path):
            await register_device(full_path, profiles)

    # event_notifier.stop()


if __name__ == "__main__":
    IOLoop.current().add_callback(main)
    IOLoop.current().start()
