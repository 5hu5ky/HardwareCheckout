from configparser import ConfigParser

from tornado.web import authenticated, MissingArgumentError
from werkzeug.security import generate_password_hash
from tornado_sqlalchemy import as_future

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
            return
        elif req_type == "addDevice":
            try:
                file = self.request.files['config'][0]
                device_type = self.get_argument("type")
            except KeyError:
                return self.render("admin.html", messages="Missing device config file")

            config = ConfigParser()
            try:
                config.read_string(file['body'])
            except KeyError:
                return self.render("admin.html", messages="Error while trying to read the file")
            
            error_msg = ''
            with self.make_session() as session:
                device_type_id = await as_future(session.query(DeviceType.id).filter_by(name=device_type).one)[0]

                for section in config.sections():
                    try:
                        session.add(
                            DeviceQueue(
                                name=config[section]['username'],
                                password=generate_password_hash(
                                    config[section]["password"], 
                                    method="pbkdf2:sha256:45000"
                                ),
                                state="want-provision",
                                type=device_type_id
                            )
                        )
                    except Exception as e:
                        error_msg += str(e) + '\n'
                        continue
            
            return self.render("admin.html", messages=error_msg)