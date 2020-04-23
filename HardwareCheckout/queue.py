from sqlalchemy import func
from tornado.escape import json_decode
from tornado.web import authenticated
import tornado.websocket

from .device import device_ready
from .models import DeviceQueue, DeviceType, User, UserQueue, db
from .webutil import Blueprint, UserWSHandler

queue = Blueprint()

@queue.route("/")
class ChatSocketHandler(UserWSHandler):
    waiters = set()
    cache = []
    cache_size = 200

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    @authenticated
    def open(self):
        ChatSocketHandler.waiters.add(self)

    def on_close(self):
        ChatSocketHandler.waiters.remove(self)

    # @classmethod
    # def update_cache(cls, chat):
    #     cls.cache.append(chat)
    #     if len(cls.cache) > cls.cache_size:
    #         cls.cache = cls.cache[-cls.cache_size :]

    @classmethod
    def send_updates(cls, chat):
        # logging.info("sending message to %d waiters", len(cls.waiters))
        for waiter in cls.waiters:
            try:
                waiter.write_message(chat)
            except Exception:
                # logging.error("Error sending message", exc_info=True)
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
            
        # ChatSocketHandler.update_cache(msg)
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
            
        self.check_queue(id)
        return {'result': 'success'}

    def handle_delete(self, id):
        # TODO make async
        with self.make_session() as session:
            entry = session.query(UserQueue).filter_by(userId=self.current_user.id, type=id).first()
            if entry:
                session.delete(entry)
                session.commit() # TODO: remove?
        return {'result': 'success'}

    def check_queue(self, id):
        # TODO make async
        with self.make_session() as session:
            deviceList = session.query(DeviceQueue).filter_by(type=id, state='ready')
            for device in deviceList :
                device_ready(session, device)
                ChatSocketHandler.send_updates(msg)