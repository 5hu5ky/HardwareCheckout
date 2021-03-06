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

    def __init__(self, url, username, password, profiles, timeout = 300):
        self.url = url
        self.username = username
        self.password = password
        self.timeout = timeout
        self.profiles = profiles

    def auth_header(self, username, password):
        return {
            "Authorization": "Basic "
            + b64encode((username + ":" + password).encode()).decode()
        }

    async def connect(self):
        print("trying to connect")
        try:
            self.ws = await websocket_connect(
                HTTPRequest(url=self.url, headers=self.auth_header(self.username, self.password))
            )

            PeriodicCallback(self.keep_alive, self.timeout * 1000).start()
            IOLoop.current().add_callback(self.recv_loop)

            for files in os.listdir("/tmp/devices"):
                full_path = os.path.join("/tmp/devices", files)
                if os.path.isdir(full_path):
                    await register_device(full_path, self, self.profiles)

        except Exception:
            print("connection error")
            self.ws = None

        if self.ws is None:
            raise Exception("ws is none. Idk what happened.")

    async def recv_loop(self):
        while True:
            msg = await self.ws.read_message()
            if msg is None:
                break
            else:
                await self.handle_message(msg)

    async def keep_alive(self):
        if self.ws is None:
            await self.connect()
        else:
            print("Keep Alive")
            try:
                await self.ws.write_message(json_encode({"type": "keep-alive"}))
            except Exception:
                self.ws = None
                IOLoop.current().add_callback(self.keep_alive)

    async def handle_message(self, message):
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
            await self.kill(params)

    async def kill(self, device):
        for keys in self.profiles:
            if self.profiles[keys]["username"] == device:
                deviceName = keys
                break

        p = subprocess(
            ["pkill", "-u", "villager-" + deviceName], 
            stdout = subprocess.STREAM, 
            stderr = subprocess.STREAM
            )

        try:
            await p.wait_for_exit()
        except Exception:
            return False
        return True

    async def register_device(self, device):
        self.ws.write_message(json_encode({'type':"register", "params":device}))


class New_Device_Handler(pyinotify.ProcessEvent):
    def my_init(self, client, profiles={}):
        self.client = client
        self.profiles = profiles

    def process_IN_CREATE(self, event):
        print("New Device Created")
        register_device(event.pathname, self.client, self.profiles)


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


async def register_device(path, client, profiles):
    matches = device_re.match(path)
    if matches:
        profile_name = matches.group(1)

        clientProfile = profiles.get(profile_name, False)
        if clientProfile:
            print("Registering new Client: {}".format(clientProfile['username']))
            await client.register_device(clientProfile['username'])
            


async def main():
    profiles = get_profiles()

    newClient = Client("wss://localhost:8080/device/controller", profiles['controller']["username"], profiles['controller']["password"], profiles)
    await newClient.connect()

    # Create the watch manager
    watch_manager = pyinotify.WatchManager()

    # TODO do we need event_notifier?
    event_notifier = pyinotify.TornadoAsyncNotifier(
        watch_manager, IOLoop.current(), New_Device_Handler(client=newClient, profiles=profiles)
    )
    watch_manager.add_watch("/tmp/devices", pyinotify.IN_CREATE)

    # event_notifier.stop()


if __name__ == "__main__":
    IOLoop.current().add_callback(main)
    IOLoop.current().start()
