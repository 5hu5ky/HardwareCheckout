#!/usr/bin/env python3
from HardwareCheckout.models import TwitchStream
from HardwareCheckout.config import db_path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import argparse

parser = ArgumentParser()
parser.add_argument('-n', '--name', help="Stream name to delete", required=True)
args = parser.parse_args()

session = sessionmaker(bind=create_engine(db_path))
s = session()

streamname = s.query(DeviceQueue).filter_by(name=args.name).first()
if not device:
    print("no stream found!")
    exit(0)

s.delete(streamname)
s.commit()
