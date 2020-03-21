from flask import Blueprint, render_template, abort, request, jsonify
from flask_login import current_user, login_required
import datetime 

from . import db
from .models import User, UserQueue, DeviceQueue

checkin = Blueprint('checkin', __name__)

@checkin.route("/checkin", methods=['POST'])
@login_required
def return_device():
    """
    This path will allow a client to return their device to the queue
    """
    if current_user.isHuman:
        abort(404)
    msg = {"status":"error"}
    content = request.get_json(force=True)
    
    web_url = content['web']
    ro_url = content['web_ro']

    queuedUser = UserQueue.query.filter_by(hasDevice=False).first()
    if queuedUser:
        user = User.query.filter_by(id=queuedUser.userId)
        if user and not user.hasDevice:
            user.hasDevice = True

    queueEntry = DeviceQueue(
        webUrl = web_url,
        roUrl = ro_url,
        inUse = False,
        inReadyState = queuedUser == True,
        owner = user.id if queuedUser and user else None,
        expiration = datetime.datetime.now() + datetime.timedelta(minutes=5)
    )

    DeviceQueue.add(queueEntry)
    db.session.commit()


    return jsonify(msg)
        
