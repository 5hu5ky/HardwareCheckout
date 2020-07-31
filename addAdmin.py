#!/usr/bin/env python3
from HardwareCheckout.models import User, Role
from HardwareCheckout.config import db_path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("-u","--username")
parser.add_argument("-p","--password")
args = parser.parse_args()
# parser.add_argument("Roles", nargs='+')

session = sessionmaker(bind=create_engine(db_path))
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