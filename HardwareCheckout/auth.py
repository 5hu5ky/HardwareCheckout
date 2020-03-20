from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from . import db
from .models import User

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["POST"])
def login():
    """
    Path that handles the actual logging in of users. All super basic at this point.

    :return:
    """
    email = request.form.get("email")
    password = request.form.get("password")
    remember = True if request.form.get("remember") else False

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        flash("Please check your login details and try again.")
        return redirect(url_for("auth.login"))

    login_user(user, remember=remember)
    return redirect(url_for("main.index"))


@auth.route("/login", methods=["GET"])
def login_page():
    """
    Serves the html for the login page.
    :return:
    """
    return render_template("login.html")


@auth.route("/signup", methods=["GET"])
def signup_page():
    """
    Serves the html for the signup page
    :return:
    """
    return render_template("signup.html")


@auth.route("/signup", methods=["POST"])
def signup():
    """
    Super basic signup handler

    :return:
    """
    email = request.form.get("email")
    name = request.form.get("name")
    password = request.form.get("password")

    user = User.query.filter_by(email=email).first()

    if user:
        flash("Email address already exists")
        return redirect(url_for("auth.signup"))

    new_user = User(
        email=email,
        name=name,
        password=generate_password_hash(password, method="sha256"),
        isHuman=True,
    )

    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for("auth.login"))


@auth.route("/logout")
@login_required
def logout():
    """
    Path that handles logging a user out.
    :return:
    """
    logout_user()
    return redirect(url_for("main.index"))
