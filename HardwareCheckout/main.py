from flask import Blueprint, render_template
from flask import current_app as app
from flask_login import current_user

from . import db, create_app
from .models import DeviceQueue, User

main = Blueprint('main', __name__)


@main.route('/')
def index():
    """
    Home path for the site

    :return:
    """

    if not current_user.is_anonymous and current_user.has_roles("Admin"):
        results = db.session.query(User.name, DeviceQueue.webUrl).join(User.deviceQueueEntry).all()
        show_streams = False
    else:
        results = db.session.query(User.name, DeviceQueue.roUrl).join(User.deviceQueueEntry).all()
        show_streams = True

    return render_template('index.html', terminals=results, show_streams=show_streams)


if __name__ == '__main__':
    create_app()
