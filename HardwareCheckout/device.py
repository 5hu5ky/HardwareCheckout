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
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.security import check_password_hash

from .models import DeviceQueue, DeviceType, UserQueue
from .webutil import Blueprint, DeviceWSHandler, Timer, make_session
from .queue import QueueWSHandler

device = Blueprint()


@device.route('/state')
class DeviceStateHandler(DeviceWSHandler):
    __timer = None
    __timer_dict = dict()

    def open(self):
        self.device = self.check_authentication()
        if self.device is False:
            self.close()
            return
        if self.__class__.__timer is None:
            self.__class__.__timer = Timer(self.__class__.__callback, True)
            self.__class__.__timer.start()

    def on_message(self, message):
        parsed = json_decode(message)

        # try:
        #     msgType = parsed["type"]
        # except (AttributeError, KeyError):
        #     return
        
        try:
            state    = parsed["state"]
            ssh_addr = parsed.get("ssh", None)
            web_addr = parsed.get("web", None)
            webro_addr=parsed.get("webro", None)
        except (AttributeError, KeyError):
            return
        self.device_put(state, ssh=ssh_addr, web=web_addr, web_ro=webro_addr)

    def device_put(self, state, ssh=None, web=None, web_ro=None):
        # always update the urls if available
        with self.make_session() as session:
            device = session.query(DeviceQueue).filter_by(id=self.device).first()
            if ssh:
                device.sshAddr = ssh
            if web:
                device.webUrl = web
            if web_ro:
                device.roUrl = web_ro

            # if we are transitioning to a failure state
            if state in ('provision-failed', 'deprovision-failed'):
                device.state = state

            # write to the db
            session.add(device)

        # if we are in a failure state
        if device.state in ('provision-failed', 'deprovision-failed', 'keep-alive'):
            return 

        # if the new status is invalid
        if state not in ('is-provisioned', 'is-deprovisioned', 'client-connected'):
            return
        
        # if the new status is provisioned and we are correctly in want provision
        if state == 'is-provisioned' and device.state == 'want-provision':
            self.device_ready(device)
        # if new status is deprovisioned and previous state is want deprovision
        elif state == 'is-deprovisioned' and device.state == 'want-deprovision':
            self.provision_device(device)
            self.send_device_state('want-provision')
        # if new status is client connected and we were in queue
        elif state == 'client-connected' and device.state == 'in-queue':
            self.device_in_use(device)
        elif device.state in ('disabled', 'want-deprovision'):
            if state != 'is-deprovisioned':
                self.send_device_state('want-deprovision')
            else:
                return
        elif state not in ('is-provisioned', 'client-connected'):
            self.send_device_state('want-provision')


    def send_device_state(self, state, **kwargs):
        kwargs['state'] = state
        return self.write_message(kwargs)

    @staticmethod
    def deprovision_device(device):
        with make_session() as session:
            device.state = 'want-deprovision'
            device.expiration = None
            session.add(device)

    @staticmethod
    def provision_device(device):
        with make_session() as session:
            device.state = 'want-provision'
            device.expiration = None
            session.add(device)

    @staticmethod
    def device_ready(device):
        with make_session() as session:
            device.state = 'ready'
            device.expiration = None
            device.owner = None
            session.add(device)
        DeviceStateHandler.check_for_new_user()

    @staticmethod
    def check_for_new_owner(device):
        with make_session() as session:
            next_user = session.query(UserQueue).filter_by(type=device.type).order_by(UserQueue.id).first()
            if next_user:
                session.delete(next_user)
                return DeviceStateHandler.device_in_queue(device, next_user)

    @staticmethod
    def device_in_queue(device, next_user):
        with make_session() as session:
            device.state = 'in-queue'
            device.owner = next_user.id
            session.add(device)

        timer = Timer(DeviceStateHandler.return_device, repeat=False, timeout=1800, args=[device.id])
        timer.start()
        try:
            DeviceStateHandler.push_timer(device.id, timer)
        except KeyError:
            old_timer = DeviceStateHandler.pop_timer(device.id)
            old_timer.stop()
            del old_timer
            DeviceStateHandler.push_timer(device.id, timer)
        QueueWSHandler.send_device_info_to_user(next_user.id, device.id)
            

    @staticmethod
    def return_device(deviceID):
        with make_session() as session:
            device = session.query(DeviceQueue).filter_by(id=deviceID).one()
            DeviceStateHandler.deprovision_device(device)
        DeviceStateHandler.send_message_to_owner(device, 'device_lost')

    @staticmethod
    def device_in_use(device):
        device.state = 'in-use'
        with make_session() as session:
            session.add(device)
            session.commit()
        
        timer = Timer(DeviceStateHandler.reclaim_device, repeat=False, timeout=1800, args=[device.id])
        timer.start()
        try:
            DeviceStateHandler.push_timer(device.id, timer)
        except KeyError:
            old_timer = DeviceStateHandler.pop_timer(device.id)
            old_timer.stop()
            del old_timer
            DeviceStateHandler.push_timer(device.id, timer)
            

    @staticmethod
    def reclaim_device(deviceID):
        with make_session() as session:
            device = session.query(DeviceQueue).filter_by(id=deviceID).one()
            DeviceStateHandler.send_message_to_owner(device, 'device_reclaimed')
            DeviceStateHandler.deprovision_device(device)

    @staticmethod
    def send_message_to_owner(device, message):
        with make_session() as session:
            name = session.query(DeviceType.name).filter_by(id=device.type).one()
        QueueWSHandler.notify_user(device.owner, error=message, device=name)

    @classmethod
    def push_timer(cls, deviceID, timer):
        if cls.__timer_dict.get(deviceID, False):
            raise KeyError("device timer already registered")
        cls.__timer_dict[deviceID] = timer

    @classmethod
    def pop_timer(cls, deviceID):
        return cls.__timer_dict.pop(deviceID)

    @staticmethod
    def __callback():
        with make_session() as session:
            for device in session.query(DeviceQueue).all():
                if device.state == 'ready':
                    DeviceStateHandler.check_for_new_owner(device)
                # elif device.state == "in-queue":
                #     DeviceStateHandler.device_in_queue(device, session)
                # elif device.state == "in-use":
                #     DeviceStateHandler.device_in_use(device)
        
