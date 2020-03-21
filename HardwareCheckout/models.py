from flask_login import UserMixin
from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey, Time
from sqlalchemy.orm import relationship
from . import db


class User(UserMixin, db.Model):
    """
    Suuuuper basic User model, this will almost certainly need to be updated.
    """
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True)
    password = Column(String(100))
    name = Column(String(1000))
    hasDevice = Column(Boolean)

    #relationships
    queueEntry = relationship("userqueue")
    deviceId = Column(Integer, ForeignKey("devicequeue.id"))

class DeviceType(db.Model):
    __tablename__ = "devicetype"
    id = Column(Integer, primary_key=True)
    name = Column(String(1000))


class Device(UserMixin, db.Model):
    __tablename__ = "device"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    secret = Column(String(100))
    type = Column(Integer, ForeignKey("devicetype.id"))

class UserQueue(db.Model):
    __tablename__ = "userqueue"
    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("user.id"))
    type = Column(Integer, ForeignKey("devicetype.id"))

class DeviceQueue(db.Model):
    __tablename__ = "devicequeue"
    id = Column(Integer, primary_key=True)
    webUrl = Column(String(200))
    roUrl = Column(String(200))
    inUse = Column(Boolean)
    inReadyState = Column(Boolean)
    expiration = Column(Time)
    owner = Column(Integer, ForeignKey("user.id"))
    device = Column(Integer, ForeignKey("device.id"))

    