from base64 import b64decode
from datetime import datetime, timedelta
from functools import wraps

from flask import abort, Blueprint, request, Response, session
from flask_socketio import disconnect, join_room, Namespace, send
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.security import check_password_hash

from . import db, socketio, timer
from .models import DeviceQueue, UserQueue

device = Blueprint('device', __name__)

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


def auth_device():
    if 'Authorization' not in request.headers or not request.headers['Authorization'].startswith('Basic '):
        return None
    name, password = b64decode(request.headers['Authorization'][6:]).decode('latin1').split(':', 1)
    try:
        return DeviceQueue.query.filter_by(name=name).one()
    except NoResultFound:
        return None


def device_login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        device = auth_device()
        if not device:
            abort(Response(status=401, headers={'WWW-Authenticate': 'Basic realm="CarHackingVillage"'}))
        return func(*args, **kwargs, device=device)
    return wrapper


class DeviceNamespace(Namespace):
    def on_connect(self):
        device = auth_device()
        if not device:
            disconnect()
            return False
        session['device_id'] = device.id
        join_room('device:%i' % device.id)
        if device.state in ('ready', 'in-queue', 'in-use', 'want-provision'):
            send_device_state(device, 'want-provision')
        elif device.state in ('disabled', 'want-deprovision'):
            send_device_state(device, 'want-deprovision')
        else:
            send_device_state(device, 'error')

    def on_message(self, json):
        device_id = session['device_id']
        try:
            device = DeviceQueue.query.filter_by(id=device_id).one()
        except NoResultFound:
            disconnect()
            return False
        device_put.__wrapped__.__wrapped__(**json, device=device)


def json_api(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        json = request.get_json()
        if not json:
            abort(415)
        json.update(kwargs)
        return func(*args, **json)
    return wrapper


@device.route('/state', methods=['PUT'])
@device_login_required
@json_api
def device_put(device, state, ssh=None, web=None, web_ro=None):
    device.sshAddr = ssh
    device.webUrl = web
    device.roUrl = web_ro
    db.session.add(device)
    db.session.commit()
    if state in ('provision-failed', 'deprovision-failed'):
        device.state = state
        db.session.add(device)
        db.session.commit()
        return {'result', 'success'}
    if device.state in ('provision-failed', 'deprovision-failed'):
        return {'result': 'error', 'error': 'device disabled'}
    if state not in ('is-provisioned', 'is-deprovisioned'):
        return {'result': 'error', 'error': 'invalid state'}, 400
    if state == 'is-provisioned' and device.state == 'want-provision':
        device_ready(device)
    elif state == 'is-deprovisioned' and device.state == 'want-deprovision':
        provision_device(device)
    elif device.state in ('disabled', 'want-deprovision'):
        if state != 'is-deprovisioned':
            send_device_state(device, 'want-deprovision')
        else:
            return {'result': 'success'}
    elif state != 'is-provisioned':
        send_device_state(device, 'want-provision')
    return {'result': 'success'}


def state_callback(device_id):
    def callback():
        device = DeviceQueue.query.filter_by(id=device_id).one()
        {
            'ready': device_ready,
            'in-queue': device_in_queue,
            'in-use': device_in_use
        }[device.state](device)
    return callback


def device_ready(device):
    device.state = 'ready'
    device.expiration = None
    device.owner = None
    db.session.add(device)
    db.session.commit()
    next_user = UserQueue.query.filter_by(type=device.type).order_by(UserQueue.id).first()
    if next_user:
        db.session.delete(next_user)
        return device_in_queue(device, next_user)


def device_in_queue(device, next_user=None):
    device.state = 'in-queue'
    if next_user is not None:
        device.owner = next_user.id
        device.expiration = datetime.now() + timedelta(minutes=5)
        send_message_to_owner(device, 'device_available')
    db.session.add(device)
    db.session.commit()
    if datetime.now() < device.expiration:
        delta = device.expiration - datetime.now()
        timer.rm_timer(device.timer)
        device.timer = timer.add_timer(state_callback(device.id), delta.total_seconds() + 1)
        db.session.add(device)
        db.session.commit()
        return
    else:
        send_message_to_owner(device, 'device_lost')
        return deprovision_device(device)


def device_in_use(device, reset_timer=False):
    device.state = 'in-use'
    if reset_timer:
        device.expiration = datetime.now() + timedelta(minutes=30)
    if datetime.now() < device.expiration:
        delta = device.expiration - datetime.now()
        timer.rm_timer(device.timer)
        device.timer = timer.add_timer(state_callback(device.id), delta.total_seconds() + 1)
        db.session.add(device)
        db.session.commit()
        return
    else:
        send_message_to_owner(device, 'device_reclaimed')
        return deprovision_device(device)


def deprovision_device(device):
    device.state = 'want-deprovision'
    device.expiration = None
    timer.rm_timer(device.timer)
    db.session.add(device)
    db.session.commit()
    send_device_state(device, 'want-deprovision')


def provision_device(device):
    device.state = 'want-provision'
    device.expiration = None
    timer.rm_timer(device.timer)
    db.session.add(device)
    db.session.commit()
    send_device_state(device, 'want-provision')


def send_device_state(device, state, **kwargs):
    kwargs['state'] = state
    return socketio.send(kwargs, json=True, namespace='/device', room='device:%i' % device.id)


def send_message_to_owner(device, message):
    return socketio.send({'message': message, 'device': device.type}, json=True, namespace='/queue', room='user:%i' % device.owner)


def restart_all_timers():
    for device in DeviceQueue.query:
        if device.state in ('ready', 'in-queue', 'in-use'):
            {
                'ready': device_ready,
                'in-queue': device_in_queue,
                'in-use': device_in_use
            }[device.state](device)
