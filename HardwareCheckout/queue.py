from sqlalchemy import event
from tornado.web import authenticated, RequestHandler
from tornado.websocket import WebSocketClosedError, WebSocketHandler
from tornado_sqlalchemy import SessionMixin, as_future

from .models import DeviceType, UserQueue, User
from .webutil import Blueprint, Waiters, UserBaseHandler

queue = Blueprint()


def on_user_assigned_device(userId, device):
    # TODO: set timer
    device_info = {'name': device.type_obj.name, 'sshAddr': device.sshAddr, 'webUrl': device.webUrl}
    message = {'type': 'new_device', 'device': device_info}
    return QueueWSHandler.waiters[userId].send(message)

@event.listens_for(UserQueue, 'after_delete')
def on_userqueue_delete(mapper, connection, target):
    message = {'type': 'queue_shrink', 'queue': target.type}
    QueueWSHandler.waiters.broadcast(message)


@event.listens_for(UserQueue, 'after_insert')
def on_userqueue_insert(mapper, connection, target):
    message = {'type': 'queue_grow', 'queue': target.type}
    QueueWSHandler.waiters.broadcast(message)


@queue.route("/event")
class QueueWSHandler(UserBaseHandler, WebSocketHandler):
    waiters = Waiters()

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

    async def open(self):
        if self.current_user:
            self.waiters[self.current_user.id].add(self)
            # send all devices, in case WS connecton was terminated then re-established
            # and a device was assigned in the meantime
            with self.make_session() as session:
                devices = await self.current_user.get_owned_devices_async(session)
                devices = [{'name': a[0], 'sshAddr': a[1], 'webUrl': a[2]} for a in devices]
                self.write_message({'type': 'all_devices', 'devices': devices})
        else:
            # support updating queue numbers even if not logged in
            self.waiters[-1].add(self)

    # TODO: find out when this runs and how to make it async
    def send(self, message):
        """Callback for webutil.Waiters"""
        try:
            return self.write_message(message)
        except WebSocketClosedError:
            self.on_close()

    def on_message(self, message):
        """Callback from received WebSocket message."""
        print("Unhandled message received on websocket: {}".format(message))

    def on_close(self):
        if self.current_user:
            QueueWSHandler.waiters[self.current_user.id].remove(self)
        else:
            QueueWSHandler.waiters[-1].remove(self)


@queue.route('/')
class ListAllQueuesHandler(SessionMixin, RequestHandler):
    async def get(self):
        queues = await DeviceType.get_queues_async(self.session)
        self.write({'result': [{'id': id, 'name': name, 'size': size} for id, name, size in queues]})


@queue.route(r'/(\d+)')
class SingleQueueHandler(UserBaseHandler):
    async def get(self, id):
        # TODO: Should this be a restricted function?
        try:
            id = int(id)
        except ValueError:
            self.render("error.html", error="Invalid Queue")
            return

        with self.make_session() as session:
            names = await as_future(session.query(User.name).select_from(UserQueue).join(User).filter(UserQueue.type == id).order_by(UserQueue.id).all)
        self.write({'result': [{'name': name} for name in names]})
        # self.redirect(self.reverse_url("main"))

    @authenticated
    async def post(self, id):
        try:
            id = int(id)
        except ValueError:
            self.render("error.html", error="Invalid Queue")
            return

        current_user_id = self.current_user.id

        with self.make_session() as session:
            # Check if the user is already registered for a queue
            entry = await as_future(session.query(UserQueue).filter_by(userId=current_user_id, type=id).first)
            if entry:
                self.render("error.html", error="User already registered for this queue")
            else:
                # Add user to the queue
                newEntry = UserQueue(userId=current_user_id, type=id)
                session.add(newEntry)
                # Send them back to the front page
                self.redirect(self.reverse_url("main"))

            # Check if someone is able to claim a device
            self.current_user.try_to_claim_device(session, id, on_user_assigned_device)

