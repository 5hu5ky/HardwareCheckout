from base64 import b64decode
from functools import partial
from contextlib import contextmanager

from tornado.web import RequestHandler, URLSpec, WebSocketHandler
from tornado.ioloop import IOLoop
from tornado_sqlalchemy import SessionMixin
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.security import check_password_hash

from .models import DeviceQueue, User, db


class UserBaseHandler(SessionMixin, RequestHandler):
    def get_current_user(self):
        try:
            user_id = self.get_secure_cookie('user')
            with self.make_session() as session:
                return session.query(User).filter_by(id=user_id).one()
        except NoResultFound:
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

class UserWSHandler(SessionMixin, WebSocketHandler):
    def get_current_user(self):
        try:
            user_id = self.get_secure_cookie('user')
            with self.make_session() as session:
                return session.query(User).filter_by(id=user_id).one()
        except NoResultFound:
            return False

class DeviceWSHandler(SessionMixin, WebSocketHandler):
    def get_current_user(self):
        # not allowed to be async
        if 'Authorization' not in self.request.headers:
            return self.unauthorized()
        if not self.request.headers['Authorization'].startswith('Basic '):
            return self.unauthorized()
        name, password = b64decode(self.request.headers['Authorization'][6:]).decode().split(':', 1)
        try:
            with self.make_session() as session:
                device = session.query(DeviceQueue).filter_by(name=name).one()
            if not check_password_hash(device.password, password):
                return self.unauthorized()
            return device
        except NoResultFound:
            return self.unauthorized()

    def unauthorized(self):
        self.set_header('WWW-Authenticate', 'Basic realm="CarHackingVillage"')
        self.set_status(401)
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
            self.__timer = IOLoop.current().PeriodicCallback(partial(self.__callback_wrapper, self), self.__timeout * 1000)

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
        else:
            self.__timer = IOLoop.current().call_later(self.__timeout, self.__callback_wrapper, self)

    def __stop(self):
        if self.__repeat:
            self.__timer.stop()
        else:
            IOLoop.current().remove_timeout(self.__timer)

    def __callback_wrapper(self):
        try:
            self.__callback(*self.__args, **self.__kwargs)
        except Exception:
            pass
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