#!/usr/bin/env python3
from HardwareCheckout.models import TwitchStream
from HardwareCheckout.config import db_path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("type", help="Stream name to add")
args = parser.parse_args()


session = sessionmaker(bind=create_engine(db_path))
s = session()
s.add(TwitchStream(name=args.type))
s.commit()