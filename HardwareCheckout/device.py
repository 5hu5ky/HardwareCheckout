from base64 import b64decode
from datetime import datetime, timedelta

from flask import abort, Blueprint, request, Response
from functools import wraps
from werkzeug.security import check_password_hash

from . import db, socketio, timer
from .models import DeviceQueue, UserQueue

device = Blueprint('device', __name__)


def auth_device(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'Authorization' not in request.headers or not request.headers['Authorization'].startswith('Basic '):
            abort(Response(status=401, headers={'WWW-Authenticate': 'Basic realm="CarHackingVillage"'}))
        name, password = b64decode(request.headers['Authorization'][6:]).decode('latin1').split(':', 1)
        device = DeviceQueue.query.filter_by(name=name).one()
        if not device or not check_password_hash(device.password, password):
            abort(403)
        return func(*args, **kwargs, device=device)
    return wrapper


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
@auth_device
@json_api
def device_put(device, state, ssh=None, web=None, web_ro=None):
    device.sshAddr = ssh
    device.webUrl = web
    device.roUrl = web_ro
    db.session.add(device)
    if state not in ('ready', 'in-use', 'provisioning'):
        return {'result': 'error', 'error': 'invalid state'}, 400
    if state == device.state:
        db.session.commit()
        return {'result': 'success'}
    {
        'ready': device_ready,
        'in-use': device_in_use,
        'provisioning': device_provisioning
    }[state](device)
    return {'result': 'success'}


def device_ready(device):
    device_id = device.id
    if device.state == 'in-queue':
        if datetime.now() < device.expiration:
            delta = device.expiration - datetime.now()
            timer.rm_timer(device.timer)
            device.timer = timer.add_timer(lambda: device_ready(DeviceQueue.query.filter_by(id=device_id).one()), delta.total_seconds() + 1)
            db.session.add(device)
            db.session.commit()
            return
        else:
            socketio.send({'message': 'device_lost', 'device': device.type}, json=True, room=str(device.owner))
    next_user = UserQueue.query.filter_by(type=device.type).order_by(UserQueue.id).first()
    if not next_user:
        device.state = 'ready'
        device.expiration = None
        device.owner = None
    else:
        device.state = 'in-queue'
        device.expiration = datetime.now() + timedelta(minutes=5)
        device.owner = next_user.id
        device.timer = timer.add_timer(lambda: device_ready(DeviceQueue.query.filter_by(id=device_id).one()), 301)
        socketio.send({'message': 'device_available', 'device': device.type}, json=True, room=str(next_user.id))
        db.session.delete(next_user)
    db.session.add(device)
    db.session.commit()


def device_in_use(device):
    device.state = 'in-use'
    device.expiration = datetime.now() + timedelta(minutes=30)
    timer.rm_timer(device.timer)
    db.session.add(device)
    db.session.commit()


def device_provisioning(device):
    device.state = 'provisioning'
    device.expiration = None
    db.session.add(device)
    db.session.commit()


def restart_all_timers():
    for device in DeviceQueue.query:
        if device.state in ('ready', 'in-queue'):
            device_ready(device)
