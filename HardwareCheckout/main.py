from .models import DeviceQueue, DeviceType, User, UserQueue
from .webutil import Blueprint, UserBaseHandler, Timer, make_session
from tornado_sqlalchemy import as_future
from sqlalchemy import func, or_

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
                try:
                    current_user = await as_future(session.query(User).filter_by(id=self.current_user).one)
                except Exception:
                    pass
                else:
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
    async def updateQueues(cls):
        '''
        TODO: I couldn't get this to work with the functions in DeviceQueue and DeviceType. Don't know why.
        '''
        with make_session() as session:
            cls.RWTerminals = await as_future(session.query(User.name, DeviceQueue.webUrl).join(User.deviceQueueEntry).filter_by(state="in-use").all)
            cls.ROTerminals = await as_future(session.query(User.name, DeviceQueue.roUrl).join(User.deviceQueueEntry).filter_by(state="in-use").all)
            cls.queues      = await as_future(session.query(DeviceType.id, DeviceType.name, func.count(UserQueue.userId)).select_from(DeviceType).join(UserQueue, isouter=True).group_by(DeviceType.id, DeviceType.name).all)
