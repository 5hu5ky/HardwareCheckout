#!/usr/bin/env python3
from HardwareCheckout.models import DeviceType
from HardwareCheckout.config import db_path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-t', '--type', help="Device type to add")
args = parser.parse_args()


session = sessionmaker(bind=create_engine(db_path))
s = session()
s.add(DeviceType(name=args.type))
s.commit()