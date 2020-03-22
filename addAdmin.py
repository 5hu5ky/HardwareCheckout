#!/usr/bin/env python3
from HardwareCheckout.models import User, Role
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("username")
parser.add_argument("password")
args = parser.parse_args()
# parser.add_argument("Roles", nargs='+')

session = sessionmaker(bind=create_engine('sqlite:///HardwareCheckout/db.sqlite'))
s = session()

admin = s.query(Role).filter_by(name="Admin").first()
human = s.query(Role).filter_by(name="Human").first()
device = s.query(Role).filter_by(name="Device").first()

s.add(
    User(
        name=args.username, 
        password=generate_password_hash(
            args.password, 
            method="pbkdf2:sha256:45000"
        ),
        roles=[admin, human, device]
    )
)
s.commit()