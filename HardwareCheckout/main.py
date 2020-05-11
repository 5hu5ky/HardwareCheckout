from .models import DeviceQueue, DeviceType
from .webutil import Blueprint, noself, UserBaseHandler, Timer, make_session
from tornado_sqlalchemy import as_future

main = Blueprint()


@main.route('/', name="main")
class MainHandler(UserBaseHandler):
    timer = None
    RWTerminals = []
    ROTerminals = []
    queues = []

    async def get(self):
        """
        Home path for the site

        :return:
        """
        # If no background queue update thread as started, start it
        if self.timer is None:
            self.timer = Timer(self.updateQueues, timeout=5, args=(self.__class__,))

        # find out what kind of terminals this user is allowed to look at
        if self.current_user and self.current_user.has_roles('Admin'):
            terminals = self.RWTerminals
            show_streams = False
        else:
            terminals = self.ROTerminals
            show_streams = True

        # check if use is logged in
        if self.current_user:
            # Get any devices the user may own.
            with self.make_session() as session:
                devices = await self.current_user.get_owned_devices_async(session)
            devices = [{'name': a[0], 'sshAddr': a[1], 'webUrl': a[2]} for a in devices]

            # get a listing of all the queues available
            # Make a copy of the list because we are iterating through it
            tqueues = self.queues
            queues = [{"id": i[0], "name": i[1], "size": i[2]} for i in tqueues]
        else:
            devices = []
            queues = []


        # TODO: limit the number of vars passed to the template
        self.render('index.html', **noself(locals()))

    @classmethod
    async def updateQueues(cls):
        with make_session() as session:
            cls.RWTerminals = await as_future(DeviceQueue.get_all_web_urls_async(session))
            cls.ROTerminals = await DeviceQueue.get_all_ro_urls_async(session)
            cls.queues = await DeviceType.get_queues_async(session)