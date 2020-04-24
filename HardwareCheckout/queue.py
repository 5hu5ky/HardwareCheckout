from tornado.web import authenticated, RequestHandler
from tornado.websocket import WebSocketHandler
from tornado_sqlalchemy import SessionMixin

from .models import DeviceType, UserQueue, User
from .webutil import Blueprint, Messenger, UserBaseHandler

queue = Blueprint()

user_queue_notifiers = {}


def on_user_assigned_device(user, device):
    # TODO: set timer
    if user.id in user_queue_notifiers:
        device = {'name': device.type_obj.name, 'sshAddr': device.sshAddr, 'webUrl': device.webUrl}
        message = {'type': 'new_device', 'device': device}
        user_queue_notifiers[user.id].send(message)


# Assign here to avoid cyclical import
User.assigned_device_callback = on_user_assigned_device


@queue.route("/event")
class QueueWSHandler(UserBaseHandler, WebSocketHandler):
    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    @authenticated
    async def open(self):
        if self.current_user.id not in user_queue_notifiers:
            user_queue_notifiers[self.current_user.id] = Messenger()
        notifier = user_queue_notifiers[self.current_user.id]
        devices = self.current_user.get_owned_devices(self.session)
        devices = [{'name': a[0], 'sshAddr': a[1], 'webUrl': a[2]} for a in devices]
        self.write_message({'type': 'all_devices', 'devices': devices})
        while True:
            message = await notifier.receive()
            self.write_message(message)

    def on_message(self, message):
        pass


@queue.route('/')
class ListAllQueuesHandler(SessionMixin, RequestHandler):
    async def get(self):
        queues = await DeviceType.get_queues_async(self.session)
        self.write({'result': [{'id': id, 'name': name, 'size': size} for id, name, size in queues]})


@queue.route(r'/(\d+)')
class SingleQueueHandler(UserBaseHandler):
    async def get(self, id):
        id = int(id)
        # TODO: maybe move this into an async model method
        self.write({'result': [{'name': name} for name, in self.session.query(User.name).select_from(UserQueue).join(User).filter(UserQueue.type == id).order_by(UserQueue.id)]})

    @authenticated
    async def post(self, id):
        id = int(id)
        entry = self.session.query(UserQueue).filter_by(userId=self.current_user.id, type=id).first()
        if entry:
            self.write({'result': 'success'})
            return
        entry = UserQueue(userId=self.current_user.id, type=id)
        self.session.add(entry)
        self.session.commit()
        self.current_user.try_to_claim_device(self.session, id)
        self.write({'result': 'success'})
