
from tornado.web import authenticated, MissingArgumentError

from .models import DeviceQueue, Role, DeviceType
from .webutil import Blueprint, UserBaseHandler

admin = Blueprint()

@admin.route('/', name="admin")
class AdminHandler(UserBaseHandler):
    @authenticated
    async def get(self):
        self.render('admin.html')

    @authenticated
    async def post(self):
        # Try and get the type parameter so we can decide what type of request this is
        try:
            req_type = self.get_argument("type")
        except MissingArgumentError:
            return self.render("admin.html", messages="Error in form submission")

        if req_type == "addDeviceType":
            try:
                name = self.get_argument("name")
            except MissingArgumentError:
                return self.render("admin.html", messages="Missing device type")
            with self.make_session() as session:
                session.add(DeviceType(name=name))
                session.commit()
                