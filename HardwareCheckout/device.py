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
from contextlib import contextmanager

from tornado.web import authenticated
from tornado.escape import json_decode
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.security import check_password_hash

from . import timer
from .models import DeviceQueue, DeviceType, UserQueue, db
from .webutil import Blueprint, DeviceWSHandler, Timer

device = Blueprint()

@contextmanager
def make_session():
    session = None
    try:
        session = db.sessionmaker()
        yield session
    except Exception:
        if session:
            session.rollback()
        raise
    else:
        session.commit()
    finally:
        if session:
            session.close()


@device.route('/state')
class DeviceStateHandler(DeviceWSHandler):
    __timer = None
    __timer_dict = dict()

    @authenticated
    def open(self):
        if self.__class__.__timer is None:
            self.__class__.__timer = Timer(self.__class__.__callback, True)
            self.__class__.__timer.start()
        self.device = self.current_user

    def on_message(self, message):
        parsed = json_decode(message)

        try:
            msgType = parsed["type"]
        except (AttributeError, KeyError):
            # try:
            #     self.write_message({"error":"invalid message"})
            # except Exception:
            #     pass
            return
        
        if msgType == "put":
            try:
                state    = parsed["state"]
                ssh_addr = parsed.get("ssh", None)
                web_addr = parsed.get("web", None)
                webro_addr=parsed.get("webro", None)
            except KeyError:
                return
            self.device_put(state, ssh=ssh_addr, web=web_addr, web_ro=webro_addr)

    def device_put(self, state, ssh=None, web=None, web_ro=None):
        self.device.sshAddr = ssh
        self.device.webUrl = web
        self.device.roUrl = web_ro
        with self.make_session() as session:
            session.add(device)
            session.commit()
        
        # if we are transitioning to a failure state
        if state in ('provision-failed', 'deprovision-failed'):
            device.state = state
            db.session.add(device)
            db.session.commit()
            return {'result', 'success'}

        # if we are already in a failure state
        if device.state in ('provision-failed', 'deprovision-failed'):
            return {'result': 'error', 'error': 'device disabled'}

        # if the new status is invalid
        if state not in ('is-provisioned', 'is-deprovisioned', 'client-connected'):
            return {'result': 'error', 'error': 'invalid state'}, 400
        
        # if the new status is provisioned and we are correctly in want provision
        if state == 'is-provisioned' and device.state == 'want-provision':
            with self.make_session() as session:
                self.device_ready(device, session)
        # if new status is deprovisioned and previous state is want deprovision
        elif state == 'is-deprovisioned' and device.state == 'want-deprovision':
            with self.make_session() as session:
                self.provision_device(device, session)
            self.send_device_state('want-provision')
        # if new status is client connected and we were in queue
        elif state == 'client-connected' and device.state == 'in-queue':
            with self.make_session() as session:
                self.device_in_use(device, session, True)
        elif device.state in ('disabled', 'want-deprovision'):
            if state != 'is-deprovisioned':
                send_device_state(device, 'want-deprovision')
            else:
                return {'result': 'success'}
        elif state not in ('is-provisioned', 'client-connected'):
            send_device_state(device, 'want-provision')
        return {'result': 'success'}

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
        send_message_to_owner(device, 'device_available')
            

    @staticmethod
    def return_device(deviceID):
        with make_session() as session:
            device = session.query(DeviceQueue).filter_by(id=deviceID).one()
            DeviceStateHandler.deprovision_device(device)
        send_message_to_owner(device, 'device_lost')

    @staticmethod
    def device_in_use(device, reset_timer=False):
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
            DeviceStateHandler.deprovision_device(device)
        send_message_to_owner(device, 'device_reclaimed')

    def send_device_state(self, state, **kwargs):
        kwargs['state'] = state
        return self.write_message(kwargs)

    def send_message_to_owner(self, device, message):
        name = DeviceType.query.filter_by(id=device.type).one().name
        return socketio.send({'message': message, 'device': name}, json=True, namespace='/queue', room='user:%i' % device.owner)

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
        try:
            session = db.sessionmaker()
            for device in session.query(DeviceQueue).all():
                if device.state == 'ready':
                    DeviceStateHandler.check_for_new_owner(device, session)
                # elif device.state == "in-queue":
                #     DeviceStateHandler.device_in_queue(device, session)
                # elif device.state == "in-use":
                #     DeviceStateHandler.device_in_use(device)
        except Exception:
            if session:
                session.rollback()
            raise
        else:
            session.commit()
        finally:
            session.close()
