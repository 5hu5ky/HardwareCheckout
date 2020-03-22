from flask import Blueprint, render_template, abort, request, jsonify
from flask_login import current_user, login_required
from flask_user import roles_required
import datetime 

from . import db
from .models import User, UserQueue, DeviceQueue

checkin = Blueprint('checkin', __name__)

@checkin.route("/checkin", methods=['POST'])
@roles_required("Device")
def return_device():
    """
    This path will allow a client to return their device to the queue
    """
    # import pdb
    # pdb.set_trace()
    msg = {"status":"error"}
    content = request.get_json(force=True)
    
    web_url = content['web']
    ro_url = content['web_ro']

    # TODO This loop is ugly
    while True:
        # find the first person in line
        queuedUser = db.session.query(UserQueue).filter_by(type=current_user.type).order_by(UserQueue.id).first()
        if queuedUser:
            # get their user info
            user = db.session.query(User).filter_by(id=queuedUser.userId).first()
            # make sure they don't have another device already
            if user and not user.hasDevice:
                user.hasDevice = True
                break
        else:
            break

    queueEntry = db.session.query(DeviceQueue).filter_by(id=current_user.id).first()
    if queueEntry:
        queueEntry.webUrl = web_url
        queueEntry.roUrl = ro_url
        queueEntry.inUse = False
        queueEntry.inReadyState = queuedUser == True
        queueEntry.owner = user.id if queuedUser and user else None
        queueEntry.expiration = datetime.datetime.now() + datetime.timedelta(minutes=5)
    else:
        # create a device entry for this device
        queueEntry = DeviceQueue(
            webUrl = web_url,
            roUrl = ro_url,
            inUse = False,
            inReadyState = queuedUser == True,
            owner = user.id if queuedUser and user else None,
            expiration = datetime.datetime.now() + datetime.timedelta(minutes=5),
        )
        db.session.add(queueEntry)
        
    db.session.commit()
    msg['status'] = "success"

    return jsonify(msg)

@checkin.route("/terminals", methods=["GET"])
def listTerminals():
    import pdb
    pdb.set_trace()
    results = db.session.query(DeviceQueue.roUrl).all()
    return jsonify(results)

# TODO      
# @checkin.route("/regiser/<device>", methods=["GET"])
# @roles_required("Human")
# def requestDevice(device):
#     if current_user:
#         return render_template("error.html", error="You already have a device in use.")
    

    
# TODO
# @checkin.route("/queue", methods=["GET"])
# def showQueue():
#     '''
#     This function needs to return the current queue of people and what device they are waiting on
#     '''
#     # TODO check to see if any devices are free
    

#     # TODO figure how why this is broken
#     queueOrder = db.session.query(UserQueue).select_from(User).join(User.id).order_by(UserQueue.id)

#     return jsonify(queueOrder)