"""
A brief guide to all the device states:
  * ready  - device is ready to be used but not in queue
  * in-queue - device is queued up to be used
  * in-use - device is currently being used
  * want-deprovision - server wants the device to deprovision itself
  * is-deprovisioned - device has deprovisioned itself
  * want-provision - server wants the device to provision itself
  * is-provisioned - device has provisioned itself

State transition guide:

ready -> in-queue -> in-use -> want-deprovision -> is-deprovisioned -> want-provision -> is-provisioned -> ready
             \                        /^
              ------------------------

Other states
  * provision-failed - provision script failed (non-zero exit code)
  * deprovision-failed - deprovision script failed (non-zero exit code)
  * disabled - device disabled by admin
"""

from base64 import b64decode
from datetime import datetime, timedelta
from functools import wraps, partial

from tornado.web import authenticated
from tornado.escape import json_decode
from tornado.ioloop import IOLoop
from sqlalchemy.orm.exc import NoResultFound
from tornado_sqlalchemy import as_future
from werkzeug.security import check_password_hash

from .models import DeviceQueue, DeviceType, UserQueue, User
from .webutil import Blueprint, UserBaseHandler, DeviceWSHandler, Timer, make_session
from .queue import QueueWSHandler, on_user_assigned_device

device = Blueprint()


@device.route('/state')
class DeviceStateHandler(DeviceWSHandler):
    __timer = None
    __timer_dict = dict()

    async def open(self):
        self.device = await self.check_authentication()
        if self.device is False:
            self.close()
            return
        if self.__class__.__timer is None:
            self.__class__.__timer = Timer(self.__class__.__callback, True)
            self.__class__.__timer.start()
        with make_session() as session:
            device = await as_future(session.query(DeviceQueue).filter_by(id=self.device).one)
            device.state = 'want-provision'
        self.send_device_state('want-provision')

    async def on_message(self, message):
        parsed = json_decode(message)
        
        try:
            state    = parsed["state"]
            ssh_addr = parsed.get("ssh", None)
            web_addr = parsed.get("web", None)
            webro_addr=parsed.get("webro", None)
        except (AttributeError, KeyError):
            return

        await self.device_put(state, ssh=ssh_addr, web=web_addr, web_ro=webro_addr)

    async def device_put(self, state, ssh=None, web=None, web_ro=None):
        # if the new status is invalid
        if state not in ('provisioned', 'deprovisioned', 'client-connected'):
            return

        # always update the urls if available
        with self.make_session() as session:
            device = await as_future(session.query(DeviceQueue).filter_by(id=self.device).first)
            if ssh:
                device.sshAddr = ssh
            if web:
                device.webUrl = web
            if web_ro:
                device.roUrl = web_ro

            # if we are transitioning to a failure state
            if state in ('provision-failed', 'deprovision-failed'):
                device.state = state

            oldState = device.state
            deviceID = device.id
            # write to the db
            session.add(device)



        return

        # if we are in a failure state
        if oldState in ('provision-failed', 'deprovision-failed', 'keep-alive'):
            return 
        
        # if the new status is provisioned and we are correctly in want provision
        if state == 'is-provisioned' and oldState == 'want-provision':
            await self.device_ready(deviceID)
        # if new status is deprovisioned and previous state is want deprovision
        elif state == 'is-deprovisioned' and oldState == 'want-deprovision':
            await self.provision_device(deviceID)
            await self.send_device_state('want-provision')
        # if new status is client connected and we were in queue
        elif state == 'client-connected' and oldState == 'in-queue':
            await self.device_in_use(deviceID)
        elif oldState in ('disabled', 'want-deprovision'):
            if state != 'is-deprovisioned':
                await self.send_device_state('want-deprovision')
            else:
                return
        elif state not in ('is-provisioned', 'client-connected'):
            await self.send_device_state('want-provision')


    def send_device_state(self, state, **kwargs):
        '''
        write_message returns an awaitable
        '''
        kwargs['state'] = state
        return self.write_message(kwargs)

    @staticmethod
    async def deprovision_device(deviceID):
        with make_session() as session:
            device = await as_future(session.query(DeviceQueue).filter_by(id=deviceID).first)
            device.state = 'want-deprovision'
            device.expiration = None
            session.add(device)

    @staticmethod
    async def provision_device(deviceID):
        with make_session() as session:
            device = as_future(session.query(DeviceQueue).filter_by(id=deviceID).first)
            device.state = 'want-provision'
            device.expiration = None
            session.add(device)

    @staticmethod
    async def device_ready(deviceID):
        with make_session() as session:
            device = await as_future(session.query(DeviceQueue).filter_by(id=deviceID).first)
            device.state = 'ready'
            device.expiration = None
            device.owner = None
            session.add(device)
            deviceType = device.type
        await DeviceStateHandler.check_for_new_owner(deviceID,deviceType)

    @staticmethod
    async def check_for_new_owner(deviceID, deviceType):
        with make_session() as session:
            next_user = await as_future(session.query(UserQueue).filter_by(type=deviceType).order_by(UserQueue.id).first)
            if next_user:
                await as_future(partial(session.delete, (next_user,)))
                return await DeviceStateHandler.device_in_queue(deviceID, next_user.userId)

    @staticmethod
    async def device_in_queue(deviceID, next_user):
        with make_session() as session:
            device = as_future(session.query(DeviceQueue).filter_by(id=deviceID).first)
            device.state = 'in-queue'
            device.owner = next_user
            session.add(device)

        timer = Timer(DeviceStateHandler.return_device, repeat=False, timeout=1800, args=[deviceID])
        timer.start()
        try:
            DeviceStateHandler.push_timer(deviceID, timer)
        except KeyError:
            old_timer = DeviceStateHandler.pop_timer(deviceID)
            old_timer.stop()
            del old_timer
            DeviceStateHandler.push_timer(deviceID, timer)

        with make_session() as session:
            device = await as_future(session.query(DeviceQueue).filter_by(id=deviceID).first)
            userID = await as_future(session.query(User.id).filter_by(id=next_user).first)
            await on_user_assigned_device(userID, device)
            

    @staticmethod
    async def return_device(deviceID):
        await DeviceStateHandler.deprovision_device(deviceID)
        await DeviceStateHandler.send_message_to_owner(device, 'device_lost')

    @staticmethod
    async def device_in_use(deviceID):
        with make_session() as session:
            device = await as_future(session.query(DeviceQueue).filter_by(id=deviceID).first)
            device.state = 'in-use'
            session.add(device)
        
        timer = Timer(DeviceStateHandler.reclaim_device, repeat=False, timeout=1800, args=[deviceID])
        timer.start()
        try:
            DeviceStateHandler.push_timer(deviceID, timer)
        except KeyError:
            old_timer = DeviceStateHandler.pop_timer(deviceID)
            old_timer.stop()
            del old_timer
            DeviceStateHandler.push_timer(deviceID, timer)
            

    @staticmethod
    async def reclaim_device(deviceID):
        await DeviceStateHandler.send_message_to_owner(deviceID, 'device_reclaimed')
        await DeviceStateHandler.deprovision_device(deviceID)

    @staticmethod
    async def send_message_to_owner(deviceID, message):
        with make_session() as session:
            owner, name = await as_future(session.query(DeviceQueue.owner, DeviceQueue.name).filter_by(id=deviceID).one)
        QueueWSHandler.notify_user(owner, error=message, device=name)

    @classmethod
    def push_timer(cls, deviceID, timer):
        '''
        not worth asyncing
        '''
        if cls.__timer_dict.get(deviceID, False):
            raise KeyError("device timer already registered")
        cls.__timer_dict[deviceID] = timer

    @classmethod
    def pop_timer(cls, deviceID):
        '''
        Not worth asyncing
        '''
        return cls.__timer_dict.pop(deviceID)

    @staticmethod
    async def __callback():
        '''
        TODO: change query to filter on ready state
        '''
        with make_session() as session:
            for deviceID, deviceType, deviceState in await as_future(session.query(DeviceQueue.id, DeviceQueue.type, DeviceQueue.state).all):
                if deviceState == 'ready':
                    DeviceStateHandler.check_for_new_owner(deviceID, deviceType)
                # elif device.state == "in-queue":
                #     DeviceStateHandler.device_in_queue(device, session)
                # elif device.state == "in-use":
                #     DeviceStateHandler.device_in_use(device)
        

@device.route('/test')
class TmateStateHandler(UserBaseHandler):
    def get(self):
        # send them home
        self.redirect(self.reverse_url("main"))
        return

    def post(self):
        try:
            data = json_decode(self.request.body)
        except Exception:
            self.redirect(self.reverse_url("main"))
            return
        
        message_type = data.get("type", None)
        entity = data.get('entity_id', None)
        user_data = data.get('userdata', None)
        params = data.get('params', None)
        if not message_type or not entity or not user_data or not params:
            self.redirect(self.reverse_url("main"))
            return


        if message_type == 'session_register':
            # check the user data to see if it is valid
            try:
                username, password = b64decode(user_data).decode().split('=')
            except Exception:
                self.redirect(self.reverse_url("main"))
                return

            # TODO check the db to see if this is valid user data
            with make_session() as session:
                try:
                    device = await as_future(session.query(DeviceQueue).filter_by(name=username).one)
                except Exception:
                    self.redirect(self.reverse_url("main"))
                    return
            
                if not check_password_hash(device.password, password):
                    self.redirect(self.reverse_url("main"))
                    return

                # register entity id with db and update ssh/web/webro info
                ssh_fmt = params.get("ssh_cmd_fmt", None)
                web_fmt = params.get("web_url_fmt", None)
                stoken = params.get("stoken", None)
                stoken_ro = params.get("stoken_ro", None)
                if not ssh_fmt or not web_fmt or not stoken or not stoken_ro:
                    self.redirect(self.reverse_url("main"))
                    return

                device.sshAddr = ssh_fmt % stoken
                device.webUrl = web_fmt % stoken
                device.roUrl = web_fmt % stoken_ro
                device.state = "provisioned"
                session.add(device)
                # TODO notify the watcher?
                # TODO start a timer

        elif message_type == "session_join":
            # Check if it is a read only session. We only care about R/W sessions
            if params.get("readonly", True):
                self.redirect(self.reverse_url("main"))
                return

            with make_session() as session:
                try:
                    device = await as_future(session.query(DeviceQueue).filter_by(entity_id=entity).one)
                except Exception:
                    self.redirect(self.reverse_url("main"))
                    return
                
                if device.state == "provisioned":
                    device.state = "in-use"
                    session.add(device)

            # TODO stop that close timer thing

        elif message_type == "session_close":
            # Technically there could be a race condition where the close message comes after the next start message.
            # In that case it is ok since the entity ID should have been updated before then.
            with make_session() as session:
                try:
                    device = await as_future(session.query(DeviceQueue).filter_by(entity_id=entity).one)
                except Exception:
                    self.redirect(self.reverse_url("main"))
                    return
                
                device.state = "deprovisioned"
                device.sshAddr = ""
                device.webUrl = ""
                device.roUrl = ""
                device.entity_id = ""
                # TODO should I null more fields?
                session.add(device)

        return
        # New tmate session
        {
            'entity_id': '0b8f6728-bbd3-11ea-9e3e-1ee9d9a0a64e', 
            'generation': 1,
            'params': {
                'client_version': '2.4.0',
                'foreground': False, 
                'ip_address': '159.203.160.47', 
                'named': False, 
                'reconnected': False, 
                'ssh_cmd_fmt': 'ssh %s@nyc1.tmate.io', 
                'ssh_only': False, 
                'stoken': 'PrReu8jmzHKzsEjkaQ7tFpPEw', 
                'stoken_ro': 'ro-5mNuxfYu5XeZnQC8R43bAcsZN', 
                'uname': {
                    'machine': 'x86_64', 
                    'nodename': 'VirtualCarHackingVillage-device1', 
                    'release': '4.15.0-66-generic', 
                    'sysname': 'Linux', 
                    'version': '#75-Ubuntu SMP Tue Oct 1 05:24:09 UTC 2019'
                }, 
                'web_url_fmt': 'https://tmate.io/t/%s', 
                'ws_url_fmt': 'wss://nyc1.tmate.io/ws/session/%s'
            }, 
            'timestamp': '2020-07-01T19:42:49.466860Z', 
            'type': 'session_register', 
            'userdata': 'some private data 10'
        }

        # New R/W Connection
        {
            'entity_id': '741e570a-bf97-11ea-bcbe-1ee9d9a0a64e', 
            'generation': 1, 
            'params': {
                'id': '7da1a46c-bf97-11ea-818b-1ee9d9a0a64e', 
                'ip_address': '73.20.184.245', 
                'readonly': False, 
                'type': 'ssh'
            }, 
            'timestamp': '2020-07-06T14:46:35.693473Z', 
            'type': 'session_join', 
            'userdata': 'some private data '
        }

        # Close Connection
        {
            'entity_id': '741e570a-bf97-11ea-bcbe-1ee9d9a0a64e', 
            'generation': 1, 
            'params': {}, 
            'timestamp': '2020-07-06T14:46:50.102141Z', 
            'type': 'session_close', 
            'userdata': 'some private data '
        }