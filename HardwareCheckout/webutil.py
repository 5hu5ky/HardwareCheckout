from base64 import b64decode
from functools import partial
from contextlib import contextmanager
from asyncio import iscoroutine

from sqlalchemy.orm.exc import NoResultFound
from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.locks import Condition
from tornado.web import RequestHandler, URLSpec
from tornado.websocket import WebSocketHandler
from tornado_sqlalchemy import SessionMixin, as_future
from werkzeug.security import check_password_hash

from .models import DeviceQueue, User, db


class UserBaseHandler(SessionMixin, RequestHandler):
    def get_current_user(self):
        try:
            user_id = int(self.get_secure_cookie('user'))
            return self.session.query(User).filter_by(id=user_id).one()
        except NoResultFound:
            return False
        except TypeError:
            return False


class DeviceBaseHandler(SessionMixin, RequestHandler):
    def get_current_user(self):
        if 'Authorization' not in self.request.headers:
            return self.unauthorized()
        if not self.request.headers['Authorization'].startswith('Basic '):
            return self.unauthorized()
        name, password = b64decode(self.request.headers['Authorization'][6:]).decode().split(':', 1)
        try:
            device = DeviceQueue.query.filter_by(name=name).one()
            if not check_password_hash(device.password, password):
                return self.unauthorized()
            return device
        except NoResultFound:
            return self.unauthorized()

    def unauthorized(self):
        self.set_header('WWW-Authenticate', 'Basic realm="CarHackingVillage"')
        self.set_status(401)
        return False


class DeviceWSHandler(SessionMixin, WebSocketHandler):
    async def check_authentication(self):
        if 'Authorization' not in self.request.headers:
            return False
        if not self.request.headers['Authorization'].startswith('Basic '):
            return False
        name, password = b64decode(self.request.headers['Authorization'][6:]).decode().split(':', 1)
        try:
            with self.make_session() as session:
                deviceID, devicePassword = await as_future(session.query(DeviceQueue.id, DeviceQueue.password).filter_by(name=name).one)
            if not check_password_hash(devicePassword, password):
                return False
            return deviceID
        except NoResultFound:
            return False



class Blueprint:
    def __init__(self):
        self.routes = []

    def route(self, path, kwargs=None, name=None):
        def decorator(cls):
            self.routes.append({
                'pattern': [part for part in path.split('/') if part],
                'handler': cls,
                'kwargs': kwargs,
                'name': name
            })
            return cls

        return decorator

    def publish(self, base):
        finalRoutes = []
        base = [part for part in base.split('/') if part]
        for route in self.routes:
            route['pattern'] = '/' + '/'.join(base + route['pattern'])
            finalRoutes.append(URLSpec(**route))
        return finalRoutes


def noself(dict):
    return {k: v for k, v in dict.items() if k != 'self'}


class Waiters:
    def __init__(self):
        self.waiters = dict()

    def __getitem__(self, id):
        if id not in self.waiters:
            self.waiters[id] = WaiterBucket()
        return self.waiters[id]

    # TODO can this be async?
    def broadcast(self, message):
        for bucket in self.waiters.values():
            bucket.send(message)


class WaiterBucket:
    def __init__(self):
        self.bucket = set()

    def __getattr__(self, name):
        return getattr(self.bucket, name)

    def remove(self, waiter):
        if waiter in self.bucket:
            self.bucket.remove(waiter)

    def send(self, message):
        for waiter in self.bucket:
            waiter.on_sent(message)


class Timer():
    __instance = None
    __timer = None
    __callback = None
    __repeat = True
    __args = []
    __kwargs = {}

    def __init__(self, func, repeat=True, timeout=10, args=None, kwargs=None):
        self.__callback = func
        self.__repeat = repeat
        self.__timeout = timeout
        self.__args = args if args else list()
        self.__kwargs = kwargs if kwargs else dict()
        if self.__repeat:
            self.__timer = PeriodicCallback(self.__callback_wrapper, self.__timeout * 1000)
            self.__timer.start()

    def restart(self):
        if self.__timer is not None:
            self.__stop()
            self.__start()

    def start(self):
        if self.__timer is None:
            self.__start()

    def stop(self):
        if self.__timer is not None:
            self.__stop()

    def __start(self):
        if self.__repeat and not self.__timer.is_running():
            self.__timer.start()
        # else:
        #     print("calling later")
        #     self.__timer = IOLoop.current().call_later(self.__timeout, self.__callback_wrapper, self)

    def __stop(self):
        if self.__repeat:
            self.__timer.stop()
        else:
            IOLoop.current().remove_timeout(self.__timer)

    def __callback_wrapper(self):
        IOLoop.current().add_callback(self.__callback, *self.__args, **self.__kwargs)
        if self.__repeat:
            self.__start()


@contextmanager
def make_session():
    session = None
    try:
        session = db.sessionmaker()
        yield session
    except Exception:
        if session:
            session.rollback()
        raise
    else:
        session.commit()
    finally:
        if session:
            session.close()
