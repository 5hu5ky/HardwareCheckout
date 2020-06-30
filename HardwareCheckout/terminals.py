import datetime
from tornado.web import RequestHandler, MissingArgumentError, authenticated
from tornado_sqlalchemy import as_future

# from . import db, socketio
from .models import User, UserQueue, DeviceQueue, DeviceType
from .webutil import Blueprint, UserBaseHandler 

terms = Blueprint()

@terms.route("/terminals", name="ROTerminals")
class ROTerminalHandler(UserBaseHandler):
    @authenticated
    async def get(self):
        with self.make_session() as session:
            results = DeviceQueue.get_all_ro_urls(session)
        self.write({"urls":results})

@terms.route("/terminals/rw")
class RWTerminalHandler(UserBaseHandler):
    @authenticated
    async def get(self):
        if not self.current_user.has_roles("Admin"):
            self.redirect(self.reverse_url("ROTerminals"))

        with self.make_session() as session:
            results = await as_future(session.query(DeviceQueue.name,DeviceQueue.webUrl,DeviceQueue.sshAddr,DeviceQueue.state).all)
        self.write({"urls":results})