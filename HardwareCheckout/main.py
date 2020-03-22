from flask import Blueprint, render_template
from flask import current_app as app

from . import db, create_app
from .models import DeviceQueue, User

main = Blueprint('main', __name__)


@main.route('/')
def index():
    """
    Home path for the site

    :return:
    """
    results = db.session.query(User.name, DeviceQueue.roUrl).join(User.deviceQueueEntry).all()
    return render_template('index.html', terminals=results)


if __name__ == '__main__':
    create_app()
