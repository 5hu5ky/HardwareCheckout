from tornado.web import RequestHandler, MissingArgumentError, authenticated
from werkzeug.security import generate_password_hash, check_password_hash
from tornado_sqlalchemy import SessionMixin

from .models import User, Role, db
from .blueprint import Blueprint

auth = Blueprint()


class Handler(SessionMixin, RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")


@auth.route("/login", name="login")
class LoginHandler(Handler):
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

        with self.make_session() as session:
            user = session.query(User).filter_by(name=name).first()

        if not user or not check_password_hash(user.password, password):
            return self.render("login.html", messages="Invalid username or password")

        self.set_secure_cookie("user", name)
        return self.redirect(self.reverse_url("main"))

    def get(self):
        """
        Serves the html for the login page.
        :return:
        """
        return self.render("login.html")


@auth.route("/signup")
class SignUpHandler(Handler):
    def get(self):
        """
        Serves the html for the signup page
        :return:
        """
        return self.render("signup.html")

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
                roles=[Role.query.filter_by(name="Human").first()],
            )

            session.add(new_user)
            session.commit()

        return self.redirect(self.reverse_url("login"))


@auth.route("/logout", name="logout")
class LogoutHandler(Handler):
    @authenticated
    def get(self):
        """
        Path that handles logging a user out.
        :return:
        """
        self.clear_cookie("user")
        return self.redirect(self.reverse_url("main"))
