from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy import func, or_
from sqlalchemy.orm import relationship

# from . import db
from .config import db_path
from tornado_sqlalchemy import SQLAlchemy, as_future
from functools import partial

db = SQLAlchemy(url=db_path, engine_options={
    "max_overflow": 15,
    "pool_pre_ping": True,
    "pool_recycle": 60 * 60,
    "pool_size": 30,
})

class User(db.Model):
    """
    Suuuuper basic User model, this will almost certainly need to be updated.
    """

    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    password = Column(String(93), unique=True)
    ctf = Column(Integer)
    name = Column(String(1000))

    # relationships
    roles = relationship("Role", secondary="user_roles")
    userQueueEntry = relationship("UserQueue")
    deviceQueueEntry = relationship("DeviceQueue", foreign_keys="DeviceQueue.owner")

    def get_owned_devices(self, session):
        return session.query(
            DeviceType.name, DeviceQueue.sshAddr, DeviceQueue.webUrl, DeviceQueue.id
        ).join(
            DeviceType
        ).filter(
            or_(DeviceQueue.state == "in-queue", DeviceQueue.state == "in-use"),
            DeviceQueue.owner == self.id,
        )

    def get_owned_devices_async(self, session):
        return as_future(self.get_owned_devices(session).all)

    def has_roles(self, role):
        # TODO: return role in self.roles
        for r in self.roles:
            if r.name == role:
                return True
        return False


class Role(db.Model):
    __tablename__ = "roles"
    id = Column(Integer(), primary_key=True)
    name = Column(String(50), unique=True)


class UserRoles(db.Model):
    __tablename__ = "user_roles"
    id = Column(Integer(), primary_key=True)
    user_id = Column(Integer(), ForeignKey("user.id", ondelete="CASCADE"))
    role_id = Column(Integer(), ForeignKey("roles.id", ondelete="CASCADE"))


class DeviceType(db.Model):
    __tablename__ = "devicetype"
    id = Column(Integer, primary_key=True)
    name = Column(String(250), unique=True)
    enabled = Column(Integer)


class UserQueue(db.Model):
    __tablename__ = "userqueue"
    id = Column(Integer, primary_key=True)
    userId = Column(Integer, ForeignKey("user.id"))
    type = Column(Integer, ForeignKey("devicetype.id"))


class DeviceQueue(db.Model):
    __tablename__ = "devicequeue"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True)
    password = Column(String(93), unique=True)
    entity_id = Column(String(200), unique=True)
    sshAddr = Column(String(200))
    webUrl = Column(String(200))
    roUrl = Column(String(200))
    state = Column(String(200))
    ctf = Column(Integer)

    owner = Column(Integer, ForeignKey("user.id"))
    type = Column(Integer, ForeignKey("devicetype.id"))
    type_obj = relationship("DeviceType")

    @staticmethod
    def get_all_web_urls(session):
        return (
            session.query(User.name, DeviceQueue.webUrl)
            .join(User.deviceQueueEntry)
            .filter_by(state="in-use")
        )

    @staticmethod
    def get_all_ro_urls(session):
        return (
            session.query(User.name, DeviceQueue.roUrl)
            .join(User.deviceQueueEntry)
            .filter_by(state="in-use")
        )

    @staticmethod
    def get_all_web_urls_async(session):
        return as_future(DeviceQueue.get_all_web_urls(session).all)

    @staticmethod
    def get_all_ro_urls_async(session):
        return as_future(DeviceQueue.get_all_ro_urls(session).all)


class TwitchStream(db.Model):
    __tablename__ = "twitchstreams"
    id = Column(Integer, primary_key=True)
    name = Column(String(200))