from flask import Blueprint, render_template
from flask_login import current_user

from . import create_app

main = Blueprint('main', __name__)


@main.route('/')
def index():
    """
    Home path for the site

    :return:
    """
    terminals = [
            # todo, populate this with the actuall terminals
        ]
    if current_user.is_authenticated:
        return render_template('index.html', name=current_user.name, terminals=terminals)
    else:
        return render_template('index.html', terminals=terminals)


if __name__ == '__main__':
    app = create_app()
