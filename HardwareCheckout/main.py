from .models import DeviceQueue, DeviceType, User
from .webutil import Blueprint, UserBaseHandler, Timer, make_session
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
        # default values
        terminals = self.ROTerminals
        show_streams = True
        devices = []
        queues = []

        # If no background queue update thread as started, start it
        if self.timer is None:
            print("Scheduling")
            self.__class__.timer = Timer(self.updateQueues, timeout=5)

        # check if use is logged in
        if self.current_user:
            with self.make_session() as session:
                #check if the user is an admin
                current_user = await as_future(session.query(User).filter_by(id=self.current_user).one)
                if current_user.has_roles('Admin'):
                    terminals = self.RWTerminals
                    show_streams = False
                    devices = []
                else:
                    # Get any devices the user may own.
                    devices = await current_user.get_owned_devices_async(session)
                    devices = [{'name': a[0], 'sshAddr': a[1], 'webUrl': a[2]} for a in devices]

            # get a listing of all the queues available
            # Make a copy of the list because we are iterating through it
            tqueues = self.queues
            queues = [{"id": i[0], "name": i[1], "size": i[2]} for i in tqueues]

        self.render('index.html', devices=devices, queues=queues, show_streams=show_streams, terminals=terminals)

    @classmethod
    def updateQueues(cls):
        '''
        TODO: I couldn't get this to async. Don't know why.
        '''
        with make_session() as session:
            # Start all the queries
            # future_WebUrls = DeviceQueue.get_all_web_urls_async(session)
            # future_WebUrlsRO = DeviceQueue.get_all_ro_urls_async(session)
            # future_Queues = DeviceType.get_queues_async(session)

            # # Wait for the results
            # cls.RWTerminals = await future_WebUrls
            # cls.ROTerminals = await future_WebUrlsRO
            # cls.queues      = await future_Queues

            cls.RWTerminals = DeviceQueue.get_all_web_urls(session)
            cls.ROTerminals = DeviceQueue.get_all_ro_urls(session)
            cls.queues      = DeviceType.get_queues(session)