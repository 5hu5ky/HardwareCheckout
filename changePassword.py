#!/usr/bin/env python3
from HardwareCheckout import db, create_app
from HardwareCheckout.models import User, Role
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("-u","--username", help="User name", required=True)
parser.add_argument("-p","--password", help="User password", required=True)
args = parser.parse_args()
# parser.add_argument("Roles", nargs='+')

session = sessionmaker(bind=create_engine('sqlite:///HardwareCheckout/db.sqlite'))
s = session()

device = s.query(User).filter_by(name=args.username).first()
if not device:
    print("no device")
    exit(0)

device.password = generate_password_hash(
                args.password, 
                method="pbkdf2:sha256:45000"
            )

s.commit()