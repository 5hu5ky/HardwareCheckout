#!/usr/bin/env python3
from HardwareCheckout import db, create_app
from HardwareCheckout.models import DeviceType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sys import argv

session = sessionmaker(bind=create_engine('sqlite:///HardwareCheckout/db.sqlite'))
s = session()
s.add(DeviceType(name=argv[1]))
s.commit()