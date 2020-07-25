from configparser import ConfigParser
from functools import partial

from tornado.web import authenticated, MissingArgumentError
from werkzeug.security import generate_password_hash
from tornado_sqlalchemy import as_future

from .models import DeviceQueue, Role, DeviceType, User
from .webutil import Blueprint, UserBaseHandler
from .auth import PASSWORD_CRYPTO_TYPE

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

        errors = ''
        if req_type == "addDeviceType":
            errors = await self.addDeviceType()
        elif req_type == "addDevice":
            errors = await self.addDevice()
        elif req_type == "addAdmin":
            errors = await self.addAdmin()
        elif req_type == "changeDevicePassword":
            errors = await self.changeDevicePassword()
        elif req_type == "rmDevice":
            errors = await self.rmDevice()
        
        return self.render("admin.html", messages=errors)

    async def addDeviceType(self):
        try:
            name = self.get_argument("name")
        except MissingArgumentError:
            return "Missing device type"
        with self.make_session() as session:
            await as_future(partial(session.add,DeviceType(name=name)))
        return ''

    async def addDevice(self):
        try:
            file = self.request.files['config'][0]
            device_type = self.get_argument("device_type")
        except KeyError:
            return "Missing device config file"
        except MissingArgumentError:
            return "Missing device type"

        config = ConfigParser()
        try:
            config.read_string(file['body'])
        except KeyError:
            return "Error while trying to read the file"
        
        error_msg = ''
        with self.make_session() as session:
            device_type_id = await as_future(session.query(DeviceType.id).filter_by(name=device_type).one)

            for section in config.sections():
                try:
                    session.add(
                        DeviceQueue(
                            name=config[section]['username'],
                            password=generate_password_hash(
                                config[section]["password"], 
                                method=PASSWORD_CRYPTO_TYPE
                            ),
                            state="want-provision",
                            type=device_type_id
                        )
                    )
                except Exception as e:
                    error_msg += str(e) + '\n'
                    continue

        return error_msg
        
    async def addAdmin(self):
        try:
            username = self.get_argument("username")
            password = self.get_argument("password")
        except MissingArgumentError:
            return "Missing username or password"

        with self.make_session() as session:
            try:
                admin = await as_future(session.query(Role).filter_by(name="Admin").first)
                human = await as_future(session.query(Role).filter_by(name="Human").first)
                device = await as_future(session.query(Role).filter_by(name="Device").first)
            except Exception:
                return "Error while finding roles"

            try:
                await as_future(
                    partial(
                        session.add,
                        User(
                            name=username, 
                            password=generate_password_hash(
                                password, 
                                method=PASSWORD_CRYPTO_TYPE
                            ),
                            roles=[admin, human, device]
                        )
                    )
                )
            except Exception:
                return "Error while attempting to add user"
        return ""

    async def changeDevicePassword(self):
        try:
            username = self.get_argument("username")
            password = self.get_argument("password")
        except MissingArgumentError:
            return "Missing username or password"

        with self.make_session() as session:
            try:
                device = await as_future(session.query(DeviceQueue).filter_by(name=username).one)
                device.password = generate_password_hash(password, method=PASSWORD_CRYPTO_TYPE)
            except Exception:
                return "Error while updating password"

        return ""

    async def rmDevice(self):
        # TODO: is this safe to do? what are the implications if someone is connected?
        try:
            username = self.get_argument("username")
        except MissingArgumentError:
            return "Missing username"

        with self.make_session() as session:
            try:
                device = await as_future(session.query(DeviceQueue).filter_by(name=username).one)
                await as_future(partial(session.delete,device))
            except Exception:
                return "Failed to remove device"
        return ""