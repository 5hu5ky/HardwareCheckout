#!/usr/bin/env python3
from HardwareCheckout import db, create_app
from HardwareCheckout.models import Role
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

db.create_all(app=create_app())

session = sessionmaker(bind=create_engine('sqlite:///HardwareCheckout/db.sqlite'))
s = session()
s.add(Role(name="Human"))
s.add(Role(name="Device"))
s.add(Role(name="Admin"))

s.commit()
