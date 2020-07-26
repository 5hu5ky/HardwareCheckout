import tornado
import tornado.options

from . import create_app, create_redirect
from .config import ssl_config

tornado.options.parse_command_line()
if not ssl_config['certfile'] or not ssl_config['keyfile']:
    app = create_app()
    #httpApp.listen(8080)
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.bind(8080)
    http_server.start(0)  # forks one process per cpu
    tornado.ioloop.IOLoop.current().start()

else:
    httpApp = create_redirect()
    redirect_server = tornado.httpserver.HTTPServer(httpApp)
    #redirect_server.listen(80)
    redirect_server.bind(80)
    redirect_server.start(0)  # forks one process per cpu

    app = create_app()
    https_server = tornado.httpserver.HTTPServer(app, ssl_options={
        "certfile": ssl_config['certfile'],
        "keyfile": ssl_config['keyfile'],
        })
    #https_server.listen(443)
    https_server.bind(443)
    http_server.start(0)  # forks one process per cpu
    #app.listen(80)
    tornado.ioloop.IOLoop.current().start()
    
