import tornado

from . import create_app

app = create_app()
app.listen(8080)
tornado.ioloop.IOLoop.current().start()
