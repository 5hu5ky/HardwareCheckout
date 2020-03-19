#!/usr/bin/env python3

from flask import Flask, Blueprint, render_template, session
from .login import load_logged_in_user

indexBP = Blueprint("index", __name__, "/")

@indexBP.route("/", methods=('GET'))
def welcomePage():
    """ 
    This is the Function which serves the landing page of the website.
    """
    return render_template("templates/base.html")

@indexBP.before_app_request
def check_login():
    return load_logged_in_user()