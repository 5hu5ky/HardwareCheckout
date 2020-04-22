from .models import DeviceQueue, DeviceType
from .webutil import Blueprint, noself, UserBaseHandler
from tornado_sqlalchemy import as_future

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
                terminals = await as_future(DeviceQueue.get_all_web_urls_async(session))
                show_streams = False
            else:
                terminals = await DeviceQueue.get_all_ro_urls_async(session)
                show_streams = True
            if self.current_user:
                devices = await self.current_user.get_owned_devices(session)
            else:
                devices = []

            # TODO figure out why this one refuses to async
            tqueues = DeviceType.get_queues(session)
            queues = []
            for i in tqueues:
                queues.append({
                    "id": i[0],
                    "name": i[1],
                    "size": i[2],
                })
            # session.flush()
            
        # TODO: limit the number of vars passed to the template
        self.render('index.html', **noself(locals()))
