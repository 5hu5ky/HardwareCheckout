#!/usr/bin/env python3
from HardwareCheckout import create_app
from HardwareCheckout.models import DeviceQueue, Role, DeviceType
from HardwareCheckout.config import db_path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("username")
args = parser.parse_args()

session = sessionmaker(bind=create_engine(db_path))
s = session()

device = s.query(DeviceQueue).filter_by(name=args.username).first()
if not device:
    print("no device")
    exit(0)

s.delete(device)
s.commit()
