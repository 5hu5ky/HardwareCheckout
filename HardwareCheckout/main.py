from flask import Blueprint, render_template
from flask import current_app as app
from flask_login import current_user
from sqlalchemy import or_

from . import db, create_app
from .models import DeviceQueue, DeviceType, User

main = Blueprint('main', __name__)


@main.route('/')
def index():
    """
    Home path for the site

    :return:
    """

    if not current_user.is_anonymous and current_user.has_roles("Admin"):
        results = db.session.query(User.name, DeviceQueue.webUrl).join(User.deviceQueueEntry).filter_by(state='in-use').all()
        show_streams = False
    else:
        results = db.session.query(User.name, DeviceQueue.roUrl).join(User.deviceQueueEntry).filter_by(state='in-use').all()
        show_streams = True

    if not current_user.is_anonymous:
        devices = db.session.query(DeviceType.name, DeviceQueue.sshAddr, DeviceQueue.webUrl).filter(or_(DeviceQueue.state == 'in-queue', DeviceQueue.state == 'in-use'), DeviceQueue.owner == current_user.id).all()
    else:
        devices = []

    return render_template('index.html', devices=devices, terminals=results, show_streams=show_streams)


if __name__ == '__main__':
    create_app()
