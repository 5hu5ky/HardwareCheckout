#!/usr/bin/env python3
from HardwareCheckout import db, create_app
from HardwareCheckout.models import DeviceQueue, Role, DeviceType
from HardwareCheckout.config import db_path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from argparse import ArgumentParser
import os

parser = ArgumentParser()
parser.add_argument('-u', '--username', dest='username', required=False)
parser.add_argument('-p','--password', dest='password', required=False)
parser.add_argument('-t', '--type', dest='devtype', required=False)
parser.add_argument('-l', '--list', help='File containing list of users', dest='userlist', required=False)
args = parser.parse_args()
# parser.add_argument("Roles", nargs='+')

session = sessionmaker(bind=create_engine(db_path))
s = session()


def deviceAdd(username, password, devtype):
    device = s.query(Role).filter_by(name="Device").first()
    typeID = s.query(DeviceType).filter_by(name=devtype).first()

    if not typeID:
        print("Invalid type")
        exit(1)
    
    s.add(
    DeviceQueue(
        name=username, 
        password=generate_password_hash(
            password, 
            method="pbkdf2:sha256:45000"
        ),
        state="want-provision",
        type=typeID.id
    )
    )
    s.commit()


if args.userlist and (args.username or args.password or args.devtype):
    print ("You cannot define username, password and device type when you define a list file!!")
elif args.username and args.password and args.devtype:
    deviceAdd(args.username,args.password,args.devtype)
else:
    if not os.path.isfile(args.userlist):
        print ("User list {} doesn't exist!".format(args.userlist))
        exit(1)
    with open(args.userlist, 'r') as ulist:
        try:
            users = list(filter(bool, ulist.read().split('\n')))
            for user in users:
                components = user.split(",")
                if len(components) < 2:
                    print("Parameter missing in line {}".format(user))
                    exit(1)
                else:
                    deviceAdd(components[0].strip(),components[1].strip(),components[2].strip())
        except Exception as e:
            print("Couldn't read {}, {}".format(args.userlist, e))
            exit(1)
