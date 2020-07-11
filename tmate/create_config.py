#!/usr/bin/env python3
import configparser
import argparse
from uuid import uuid4
from os import mkdir, chmod
from base64 import b64encode

parser = argparse.ArgumentParser()
parser.add_argument("prefix", help="device name prefix")
parser.add_argument("count", type=int)
args = parser.parse_args()

def gen_password():
    return uuid4()

try:
    mkdir("/tmp/devices/")
except Exception:
    pass

config = configparser.ConfigParser()
for i in range(args.count):
    name = "device{}".format(i)
    username = "{}-{}".format(args.prefix, name)
    password = gen_password()
    path = "/root/device{}".format(i)
    config[name]={
        "username":username,
        "password":password
    }
    with open(path, 'w') as fout:
        fout.write("AUTH={}\n".format(b64encode("{}={}".format(username, password).encode())))
    chmod(path, 0o600)

config["controller"] = {
    "username": "{}-controller".format(args.prefix),
    "password": gen_password(),
}

with open("/opt/hc-client/.config.ini", "w") as confout:
    config.write(confout)
chmod("/opt/hc-client/.config.ini", 0o600)
