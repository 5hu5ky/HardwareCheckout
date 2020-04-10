from flask import Blueprint
from flask_login import current_user, login_required

from . import db
from .device import device_ready
from .models import DeviceQueue, User, UserQueue

queue = Blueprint('queue', __name__)


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
