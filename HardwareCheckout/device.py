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

    def post(self):
        try:
            data = json_decode(self.request.body)
        except Exception:
            self.redirect(self.reverse_url("main"))
        
        print(data)