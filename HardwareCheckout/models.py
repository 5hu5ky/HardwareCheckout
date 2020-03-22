from flask_user import UserMixin
from sqlalchemy import Table, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from . import db


class User(db.Model, UserMixin):
    """
    Suuuuper basic User model, this will almost certainly need to be updated.
    """
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    password = Column(String(100), unique=True)
    name = Column(String(1000))
    
    #relationships
    roles = db.relationship('Role', secondary='user_roles')
    userQueueEntry = relationship("UserQueue")
    deviceQueueEntry = relationship("DeviceQueue")
    type = Column(Integer, ForeignKey("devicetype.id"))

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)

class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))

class DeviceType(db.Model):
    __tablename__ = "devicetype"
    id = Column(Integer, primary_key=True)
    name = Column(String(250), unique=True)

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
    expiration = Column(DateTime)
    owner = Column(Integer, ForeignKey("user.id"))
    # device = Column(Integer, ForeignKey("user.id"))

    