import tornado

from . import create_app, create_redirect
from .config import ssl_config

if not ssl_config['certfile'] or not ssl_config['keyfile']:
    app = create_app()
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()

else:
    httpApp = create_redirect()
    redirect_server = tornado.httpserver.HTTPServer(httpApp)
    redirect_server.listen(80)

    app = create_app()
    http_server = tornado.httpserver.HTTPServer(app, ssl_options={
        "certfile": ssl_config['certfile'],
        "keyfile": ssl_config['keyfile'],
        })
    http_server.listen(443)
    #app.listen(80)
    tornado.ioloop.IOLoop.current().start()
    