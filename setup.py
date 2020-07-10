#!/usr/bin/env python3
from HardwareCheckout import create_app
from HardwareCheckout.models import Role, db
from HardwareCheckout.config import db_path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--clean", help="remove existing database if it exists", action="store_true")
args = parser.parse_args()

if args.clean:
    if os.path.isfile(db_path[9:]):
        os.unlink(db_path[9:])
    else:
        db.drop_all()

db.create_all()

session = sessionmaker(bind=create_engine(db_path))
s = session()
s.add(Role(name="Human"))
s.add(Role(name="Device"))
s.add(Role(name="Admin"))

s.commit()
