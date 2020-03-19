#!/usr/bin/env python3
import json
from pages.index import welcomePage
from pages.login import loginPage
from pages.checkout import checkout
from flask import Flask

app = Flask(__name__)


welcomePage = app.route("/")(welcomePage)
loginPage = app.route("/login")(loginPage)
checkout = app.route("/checkout/<uid>")(checkout)

if __name__ == "__main__":
    app.run()
