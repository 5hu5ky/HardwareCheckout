from flask import Blueprint
from flask_login import current_user, login_required
from flask_socketio import disconnect, join_room, Namespace
from sqlalchemy import func

from . import db
from .device import device_ready
from .models import DeviceQueue, DeviceType, User, UserQueue

queue = Blueprint('queue', __name__)


class QueueNamespace(Namespace):
    def on_connect(self):
        if current_user.is_authenticated:
            join_room('user:%i' % current_user.id)
        else:
            disconnect()


@queue.route('/', methods=['GET'])
def list_queues():
    return {'result': [{'id': id, 'name': name, 'size': size} for id, name, size in db.session.query(DeviceType.id, DeviceType.name, func.count(UserQueue.userId)).select_from(DeviceType).join(UserQueue, isouter=True).group_by(DeviceType.name)]}


@queue.route('/<id>', methods=['GET'])
def handle_get(id):
    return {'result': [{'name': name} for name, in db.session.query(User.name).select_from(UserQueue).join(User).filter(UserQueue.type == id).order_by(UserQueue.id)]}


@queue.route('/<id>', methods=['POST'])
@login_required
def handle_post(id):
    entry = UserQueue.query.filter_by(userId=current_user.id, type=id).first()
    if entry:
        return {'result': 'success'}
    entry = UserQueue(userId=current_user.id, type=id)
    db.session.add(entry)
    db.session.commit()
    for device in DeviceQueue.query.filter_by(type=id, state='ready'):
        device_ready(device)
    return {'result': 'success'}


@queue.route('/<id>', methods=['DELETE'])
@login_required
def handle_delete(id):
    entry = UserQueue.query.filter_by(userId=current_user.id, type=id).first()
    if entry:
        db.session.delete(entry)
    db.session.commit()
    return {'result': 'success'}
