#!/usr/bin/env python3
from HardwareCheckout import db, create_app
from HardwareCheckout.models import Role
from HardwareCheckout.config import db_path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--clean", help="remove existing database if it exists")
args = parser.parse_args()

if os.path.isfile(db_path[9:]):
    os.unlink(db_path[9:])

db.create_all(app=create_app(db_path))

session = sessionmaker(bind=create_engine(db_path))
s = session()
s.add(Role(name="Human"))
s.add(Role(name="Device"))
s.add(Role(name="Admin"))

s.commit()
