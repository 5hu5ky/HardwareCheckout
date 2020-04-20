# from tornado.web import

from .auth import Handler 
from .models import DeviceQueue, DeviceType, User, db
from .user import get_devices
from .blueprint import Blueprint

main = Blueprint()


@main.route('/', name="main")
class MainHandler(Handler):
    def get(self):
        """
        Home path for the site

        :return:
        """
        # TODO
        # if not current_user.is_anonymous and current_user.has_roles("Admin"):
        #     results = db.session.query(User.name, DeviceQueue.webUrl).join(User.deviceQueueEntry).filter_by(state='in-use').all()
        #     show_streams = False
        # else: 
        results = db.session.query(User.name, DeviceQueue.roUrl).join(User.deviceQueueEntry).filter_by(state='in-use').all()
        show_streams = True
        devices = get_devices()['result']

        from .queue import list_queues
        return self.render('index.html', devices=devices, queues=list_queues()['result'], terminals=results, show_streams=show_streams)


if __name__ == '__main__':
    
