#!/usr/bin/env python3
import configparser
import argparse
from uuid import uuid4
from os import mkdir

parser = argparse.ArgumentParser()
parser.add_argument("prefix", help="device name prefix")
parser.add_argument("count", type=int)
args = parser.parse_args()

mkdir("/tmp/devices/")

config = configparser.ConfigParser()
for i in range(args.count):
    name = "device{}".format(i)
    data_dir = "/tmp/devices/{}".format(name)
    mkdir(data_dir)
    config[name] = {
        "username": "{}-{}".format(args.prefix, name),
        "password": uuid4(),
        "data_dir": data_dir,
    }

# TODO better password generation
config["controller"] = {
    "username": "{}-controller".format(args.prefix),
    "password": uuid4(),
}

with open("/opt/hc-client/.config.ini", "w") as confout:
    config.write(confout)

