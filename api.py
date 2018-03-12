import cherrypy
import json

class Root(object):
    
    @cherrypy.expose
    def bids(self):
        %store -r
        return json.dumps({"current_round": curr_round,"last_round": last_round})

if __name__ == '__main__':
    cherrypy.config.update({
        'environment': 'production',
        'server.socket_host': '127.0.0.1',
        'server.socket_port': 6060,
        'tools.proxy.on': True,
    })
    cherrypy.tree.mount(Root(), '/')
    cherrypy.engine.start()
