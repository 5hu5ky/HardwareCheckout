from tornado.web import RequestHandler, MissingArgumentError, authenticated
from werkzeug.security import generate_password_hash, check_password_hash
from tornado_sqlalchemy import SessionMixin, as_future
from functools import partial


from .models import User, Role, db
from .webutil import Blueprint, UserBaseHandler

auth = Blueprint()


@auth.route("/login", name="login")
class LoginHandler(UserBaseHandler):
    def post(self):
        """
        Path that handles the actual logging in of users. All super basic at this point.

        :return:
        """
        try:
            name = self.get_argument("name")
            password = self.get_argument("password")
            # remember = True if request.form.get("remember") else False
        except MissingArgumentError:
            # self.write_error(400)
            return self.render("login.html", messages="Missing username or password")

        if name is None or password is None:
            # self.write_error(400)
            return self.render("login.html", messages="Invalid username or password")

        user = self.session.query(User).filter_by(name=name).first()

        if not user or not check_password_hash(user.password, password):
            return self.render("login.html", messages="Invalid username or password")

        self.set_secure_cookie("user", str(user.id))
        return self.redirect(self.reverse_url("main"))

    def get(self):
        """
        Serves the html for the login page.
        :return:
        """
        return self.render("login.html", messages=None)


@auth.route("/signup")
class SignUpHandler(UserBaseHandler):
    def get(self):
        """
        Serves the html for the signup page
        :return:
        """
        return self.render("signup.html", messages=None)

    def post(self):
        """
        Super basic signup handler

        :return:
        """
        try:
            name = self.get_argument("name")
            password = self.get_argument("password")
        except MissingArgumentError:
            return self.render("signup.html", messages="Missing username or password")

        with self.make_session() as session:
            user = session.query(User).filter_by(name=name).first()

            if user:
                return self.render("signup.html", messages="User name already exists")

            new_user = User(
                name=name,
                password=generate_password_hash(password, method="pbkdf2:sha256:45000"),
                roles=[session.query(Role).filter_by(name="Human").first()],
            )

            session.add(new_user)
            session.commit()

        return self.redirect(self.reverse_url("login"))


@auth.route("/logout", name="logout")
class LogoutHandler(UserBaseHandler):
    @authenticated
    def get(self):
        """
        Path that handles logging a user out.
        :return:
        """
        self.clear_cookie("user")
        return self.redirect(self.reverse_url("main"))
