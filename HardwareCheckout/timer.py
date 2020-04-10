import os
from base64 import urlsafe_b64encode

from flask import Blueprint


def Timer(path):
    timer = Blueprint('timer', __name__)
    map = {}

    def add_timer(callback, timeout):
        timeout = int(timeout)
        key = urlsafe_b64encode(os.urandom(32)).decode('latin-1').rstrip('=')
        if key in map:
            raise Exception('random number collision (!)')
        map[key] = callback
        if os.system('systemd-run --on-active=%i curl -X POST http://localhost:5000%s/%s' % (timeout, path, key)):
            del map[key]
            raise Exception('systemd-run failed')
        return key

    def rm_timer(key):
        try:
            del map[key]
        except KeyError:
            pass

    @timer.route('/<key>', methods=['POST'])
    def handle_timer(key):
        if key in map:
            callback = map[key]
            del map[key]
            callback()
        return ''

    timer.add_timer = add_timer
    timer.rm_timer = rm_timer
    return timer
