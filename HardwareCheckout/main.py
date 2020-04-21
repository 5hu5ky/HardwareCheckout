from .models import DeviceQueue, DeviceType
from .webutil import Blueprint, noself, UserBaseHandler, as_future

main = Blueprint()


@main.route('/', name="main")
class MainHandler(UserBaseHandler):
    async def get(self):
        """
        Home path for the site

        :return:
        """
        with self.make_session() as session:
            if self.current_user and self.current_user.has_roles('Admin'):
                terminals_future = DeviceQueue.get_all_web_urls_async(session)
                show_streams = False
            else:
                terminals_future = DeviceQueue.get_all_ro_urls_async(session)
                show_streams = True
            if self.current_user:
                devices_future = self.current_user.get_owned_devices(session)
            else:
                devices_future = as_future([])
            queues = [{'id': id, 'name': name, 'size': count} for id, name, count in await DeviceType.get_queues_async(session)]
            terminals = await terminals_future
            devices = await devices_future
        self.render('index.html', **noself(locals()))
