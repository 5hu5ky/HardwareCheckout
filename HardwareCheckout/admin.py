
from tornado.web import authenticated

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
        pass