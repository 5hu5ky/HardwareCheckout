from flask import Blueprint
from flask_login import current_user, login_required
from sqlalchemy import or_

from . import db
from .models import DeviceQueue, DeviceType

user = Blueprint('user', __name__)


@user.route('/device', methods=['GET'])
@login_required
def get_devices():
    devices = [{'name': d[0], 'sshAddr': d[1], 'webUrl': d[2]} for d in db.session.query(DeviceType.name, DeviceQueue.sshAddr, DeviceQueue.webUrl).filter(or_(DeviceQueue.state == 'in-queue', DeviceQueue.state == 'in-use'), DeviceQueue.owner == current_user.id)]
    return {'result': devices}
