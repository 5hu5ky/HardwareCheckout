from base64 import b64decode

from sqlalchemy.orm.exc import NoResultFound
from tornado.web import RequestHandler, URLSpec, WebSocketHandler
from tornado_sqlalchemy import SessionMixin
from werkzeug.security import check_password_hash

from .models import DeviceQueue, User


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
