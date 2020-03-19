from flask import Blueprint, render_template
from flask_login import current_user

from . import create_app

main = Blueprint('main', __name__)


@main.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('index.html', name=current_user.name)
    else:
        return render_template('index.html')

if __name__ == '__main__':
    app = create_app()
