import functools
from tornado.web import URLSpec

class Blueprint():
    def __init__(self):
        self.routes = []
    
    def route(self, path, kwargs=None, name=None):
        def decorator(Cls):
            self.routes.append({"path":path, "handler":Cls, "kwargs":kwargs, "name":name})
            return Cls
        return decorator

    def publish(self, base):
        finalRoutes = []
        if base[-1] != '/':
            base += '/'
        for route in self.routes:
            route['path'] = base + route['path']
            finalRoutes.append(URLSpec(**route))
        return finalRoutes