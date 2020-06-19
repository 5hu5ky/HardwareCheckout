from tornado.web import Application, RequestHandler
from tornado_sqlalchemy import SQLAlchemy
import os
import json
from datetime import datetime, timedelta

from .config import db_path
from .main import main as main_blueprint
from .auth import auth as auth_blueprint
from .terminals import terms as terminal_blueprint
from .queue import queue as queue_blueprint
from .device import device as device_blueprint

# init SQLAlchemy so we can use it later in our models

def create_redirect():
    class sslRedirect(RequestHandler):
        def get(self):
            self.redirect('https://' + self.request.host, permanent=True)
        def post(self):
            self.redirect('https://' + self.request.host, permanent=True)

    app = Application(
        [
            (r'/.*', sslRedirect)
        ]
    )
    return app

def create_app():
    """

    :return:
    """
    app = Application(
        [
            *(main_blueprint.publish('/')),
            *(auth_blueprint.publish('/')),
            *(terminal_blueprint.publish('/')),
            *(queue_blueprint.publish('/queue')),
            *(device_blueprint.publish('/device'))
        ],
        login_url="/login",
        cookie_secret=os.environ.get('TORNADO_SECRET_KEY', open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../cookie.key"),'r').read()),
        template_path="HardwareCheckout/templates/",
        static_path="HardwareCheckout/static/",
        db=SQLAlchemy(url=db_path),
        # xsrf_cookies=True,  #TODO
        websocket_ping_interval=10000,
        websocket_ping_timeout=30000,
    )

    return app # skip all below for testing without removing it

    # global socketio
    # socketio = SocketIO(app)

    # from .timer import Timer
    # global timer
    # timer = Timer()

    # from .models import User, Role
    # UserManager.USER_ENABLE_EMAIL = False
    # user_manager = UserManager(app, db, User)
    # user_manager.login_manager.login_view = 'auth.login'



    # # blueprint for auth routes in our app
    # from .auth import auth as auth_blueprint
    # app.register_blueprint(auth_blueprint)

    # # blueprint for non-auth parts of app
    # from .checkin import checkin as checkin_blueprint
    # app.register_blueprint(checkin_blueprint)
    # from .device import device as device_blueprint, restart_all_timers, DeviceNamespace
    # app.register_blueprint(device_blueprint, url_prefix='/device')
    # socketio.on_namespace(DeviceNamespace('/device'))
    # timer.add_timer('/device/timer', datetime.now() + timedelta(seconds=2))
    # from .queue import queue as queue_blueprint, QueueNamespace
    # app.register_blueprint(queue_blueprint, url_prefix='/queue')
    # socketio.on_namespace(QueueNamespace('/queue'))
    # from .user import user as user_blueprint
    # app.register_blueprint(user_blueprint, url_prefix='/user')

    # return app
