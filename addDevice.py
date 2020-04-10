#!/usr/bin/env python3
from HardwareCheckout import db, create_app
from HardwareCheckout.models import DeviceQueue, Role, DeviceType
from HardwareCheckout.config import db_path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("username")
parser.add_argument("password")
parser.add_argument("type")
args = parser.parse_args()
# parser.add_argument("Roles", nargs='+')

session = sessionmaker(bind=create_engine(db_path))
s = session()

device = s.query(Role).filter_by(name="Device").first()
typeID = s.query(DeviceType).filter_by(name=args.type).first()
if not typeID:
    print("Invalid type")
    exit(1)

s.add(
    DeviceQueue(
        name=args.username, 
        password=generate_password_hash(
            args.password, 
            method="pbkdf2:sha256:45000"
        ),
        type=typeID.id
    )
)
s.commit()
