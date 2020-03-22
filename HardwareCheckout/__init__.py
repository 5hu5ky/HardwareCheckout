from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_user import UserManager
import os
import json

# init SQLAlchemy so we can use it later in our models
db = SQLAlchemy()


def create_app():
    """

    :return:
    """
    app = Flask(__name__)

    app.config['SECRET_KEY'] = '9OLWxND4o83j4K4iuopO'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'

    db.init_app(app)


    from .models import User, Role
    UserManager.USER_ENABLE_EMAIL = False
    user_manager = UserManager(app, db, User)
    user_manager.login_manager.login_view = 'auth.login'

    # @user_manager.login_manager.user_loader
    # def load_user(user_id):
    #     """

    #     :param user_id:
    #     :return:
    #     """
    #     return User.query.get(int(user_id))

    # blueprint for auth routes in our app
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    # blueprint for non-auth parts of app
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    from .checkin import checkin as checkin_blueprint
    app.register_blueprint(checkin_blueprint)

    return app



