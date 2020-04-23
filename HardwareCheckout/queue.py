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
        if self.__class__.waiters.get(self.current_user.id, False):
            self.__class__.waiters[self.current_user.id] = [self]
        else:
            self.__class__.waiters[self.current_user.id].append(self)
        self.check_queue()

    def on_close(self):
        self.__class__.waiters[self.current_user.id].remove(self)

    @classmethod
    def notify_user(cls, userId, message):
        user = cls.waiters.get(userId, None)
        if user is None:
            raise KeyError("User not found")
        for tabs in user:
            tabs.write_message(message)

    @classmethod
    def send_updates(cls, chat):
        for waiter in cls.waiters.values():
            try:
                waiter.write_message(chat)
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
                try:
                    self.write_message({"error":"invalid id"})
                except Exception:
                    pass
                return
            msg = self.handle_post(uid)
        elif msgType == "delete":
            if uid is None:
                try:
                    self.write_message({"error":"invalid id"})
                except Exception:
                    pass
                return
            msg = self.handle_delete(id)
        else:
            try:
                self.write_message({"error":"invalid message"})
            except Exception:
                pass
            return
            
        self.write_message(msg)
        return

    def list_queues(self):
        with self.make_session() as session:
            # TODO make async
            queue = DeviceType.get_queues(session)
        return {'result': [{'id': id, 'name': name, 'size': size} for id, name, size in queue]}

    def handle_post(self, id):
        # TODO make async
        with self.make_session() as session:
            entry = session.query(UserQueue).filter_by(userId=self.current_user.id, type=id).first()
            if entry:
                return {'result': 'success'}
            entry = UserQueue(userId=self.current_user.id, type=id)
            session.add(entry)
            session.commit()
            
        return {'result': 'success'}

    def handle_delete(self, id):
        # TODO make async
        with self.make_session() as session:
            entry = session.query(UserQueue).filter_by(userId=self.current_user.id, type=id).first()
            if entry:
                session.delete(entry)
        return {'result': 'success'}

    def check_queue(self):
        # TODO make async
        with self.make_session() as session:
            deviceList = session.query(DeviceQueue.id).filter_by(owner=self.current_user.id).all()
        for device in deviceList:
            self.send_device_info_to_user(self.current_user.id, device)

    @classmethod
    def send_device_info_to_user(cls, userId, deviceId):
        # TODO make async
        with make_session() as session:
            deviceInfo = session.query(DeviceQueue.sshAddr, DeviceQueue.webUrl, DeviceQueue.name).filter_by(userId=userId).all()
        for devices in deviceInfo:
            cls.notify_user(userId, {"status":"device_available", "ssh":devices[0], "web":devices[1], "device":devices[2]})

    # @classmethod
    # def send_device_info_to_user(cls, userId, deviceId):
    #     # TODO make async
    #     with make_session() as session:
    #         deviceInfo = session.query(DeviceQueue.sshAddr, DeviceQueue.webUrl).filter_by(userId=userId).all()
    #     for devices in deviceInfo:
    #         cls.notify_user(userId, {"status":"device_lost"})