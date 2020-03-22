from flask import Blueprint, render_template
from flask import current_app as app

from . import create_app

main = Blueprint('main', __name__)


@main.route('/')
def index():
    """
    Home path for the site

    :return:
    """
    return render_template('index.html', terminals=app.config['TERMINALS'])


if __name__ == '__main__':
    create_app()
