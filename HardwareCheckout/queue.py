from sqlalchemy import func
from tornado.escape import json_decode
from tornado.web import authenticated
import tornado.websocket

from .models import DeviceQueue, DeviceType, User, UserQueue, db
from .webutil import Blueprint, UserWSHandler, make_session

queue = Blueprint()

@queue.route("/")
class QueueWSHandler(UserWSHandler):
    waiters = dict()

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    @authenticated
    def open(self):
        self.id = self.current_user.id
        if self.__class__.waiters.get(self.current_user.id, False):
            self.__class__.waiters[self.current_user.id] = [self]
        else:
            self.__class__.waiters[self.current_user.id].append(self)
        self.check_queue()

    def on_close(self):
        self.__class__.waiters[self.id].remove(self)

    @classmethod
    def notify_user(cls, userId, error="success", **kwargs):
        kwargs["error"] = error
        user = cls.waiters.get(userId, None)
        if user is None:
            raise KeyError("User not found")
        for tabs in user:
            try:
                tabs.write_message(kwargs)
            except Exception:
                pass

    @classmethod
    def notify_all(cls, error="success", **kwargs):
        kwargs['error'] = error
        for waiter in cls.waiters.values():
            try:
                waiter.write_message(kwargs)
            except Exception:
                pass

    async def on_message(self, message):
        parsed = json_decode(message)
        
        try:
            msgType = parsed["type"]
            uid = parsed.get("id", None)
        except (AttributeError, KeyError):
            try:
                self.write_message({"error":"invalid message"})
            except Exception:
                pass
            return

        if msgType == "list":
            msg = self.list_queues()
        elif msgType == "post":
            if uid is None:
                self.notify_user(self.id, error="invalid id")
                return
            if self.handle_post(uid):
                self.notify_all(**self.list_queues())
        elif msgType == "delete":
            if uid is None:
                self.notify_user(self.id, error="invalid id")
            if self.handle_delete(id):
                self.notify_all(**self.list_queues())
        else:
            self.notify_user(self.id, error="invalid message")

        self.write_message(msg)
        return

    def list_queues(self):
        with self.make_session() as session:
            # TODO make async
            queue = DeviceType.get_queues(session)
        return {'result': [{'id': id, 'name': name, 'size': size} for id, name, size in queue]}

    def handle_post(self, QueueID):
        # TODO make async
        with self.make_session() as session:
            entry = session.query(UserQueue).filter_by(userId=self.id, type=QueueID).first()
            #check to see if they are already in the queue
            if not entry:
                # if they aren't add them
                entry = UserQueue(userId=self.id, type=QueueID)
                session.add(entry)
                return True
        return False

    def handle_delete(self, QueueID):
        # TODO make async
        with self.make_session() as session:
            entry = session.query(UserQueue).filter_by(userId=self.id, type=QueueID).first()
            if entry:
                session.delete(entry)
                return True
        return False

    def check_queue(self):
        # TODO make async
        with self.make_session() as session:
            deviceList = session.query(DeviceQueue.id).filter_by(owner=self.id).all()
        for device in deviceList:
            self.send_device_info_to_user(self.id, device)

    @classmethod
    def send_device_info_to_user(cls, userId, deviceId):
        # TODO make async
        with make_session() as session:
            deviceInfo = session.query(DeviceQueue.sshAddr, DeviceQueue.webUrl, DeviceQueue.name).filter_by(userId=userId).all()
        for devices in deviceInfo:
            cls.notify_user(userId, error="device_available", ssh=devices[0], web=devices[1], device=devices[2])

    # @classmethod
    # def send_device_info_to_user(cls, userId, deviceId):
    #     # TODO make async
    #     with make_session() as session:
    #         deviceInfo = session.query(DeviceQueue.sshAddr, DeviceQueue.webUrl).filter_by(userId=userId).all()
    #     for devices in deviceInfo:
    #         cls.notify_user(userId, {"status":"device_lost"})