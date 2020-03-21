from flask_login import UserMixin
from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey, Time
from sqlalchemy.orm import relationship
from . import db


class User(UserMixin, db.Model):
    """
    Suuuuper basic User model, this will almost certainly need to be updated.
    """
    id = Column(Integer, primary_key=True)
    email = Column(String(100), unique=True)
    password = Column(String(100))
    name = Column(String(1000))
    isHuman = Column(Boolean)
    hasDevice = Column(Boolean)

    #relationships
    queueEntry = relationship("UserQueue")
    deviceId = Column(Integer, ForeignKey("DeviceQueue.id"))


class UserQueue(db.Model):
    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("User.id"))

class DeviceQueue(db.Model):
    id = Column(Integer, primary_key=True)
    webUrl = Column(String(200))
    roUrl = Column(String(200))
    inUse = Column(Boolean)
    inReadyState = Column(Boolean)
    expiration = Column(Time)
    owner = Column(Integer, ForeignKey("User.id"))