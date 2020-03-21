from flask_login import UserMixin
from . import db


class User(UserMixin, db.Model):
    """
    Suuuuper basic User model, this will almost certainly need to be updated.
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    isHuman = db.Column(db.Boolean)

