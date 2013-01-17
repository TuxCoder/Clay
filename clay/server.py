# -*- coding: utf-8 -*-
from datetime import datetime
import socket
import sys

from cheroot import wsgi


DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 8080
MAX_PORT_DELTA = 10

WELCOME = u' # Clay (by Lucuma labs)\n\n'
ADDRINUSE = u' ---- Address already in use. Trying another port...\n'
RUNNING_ON = u' * Running on http://%s:%s\n'
HOW_TO_QUIT = u' -- Quit the server with Ctrl+C --\n\n'

HTTPMSG = '500 Internal Error'


class Server(object):

    def __init__(self, clay):
        self.clay = clay
        app = RequestLogger(clay.app)
        self.dispatcher = wsgi.WSGIPathInfoDispatcher({'/': app})

    def run(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        port = port or self.clay.settings.get('port', DEFAULT_PORT)
        host = host or self.clay.settings.get('host', DEFAULT_HOST)
        max_port = port + MAX_PORT_DELTA
        sys.stdout.write(WELCOME)
        return self._testrun(host, port, max_port)

    def _testrun(self, host, current_port, max_port):
        try:
            return self._run(host, current_port)
        except socket.error, e:
            if e.errno != socket.errno.EADDRINUSE:
                sys.stdout.write(str(e))
                return
            sys.stdout.write(ADDRINUSE)
            current_port += 1
            if current_port > max_port:
                return
            self._testrun(host, current_port, max_port)

    def _run(self, host, port):
        self.print_help_msg(host, port)
        server = self._get_wsgi_server(host, port)
        try:
            return server.start()
        except KeyboardInterrupt:
            server.stop()

    def _get_wsgi_server(self, host, port):
        return wsgi.WSGIServer((host, port), wsgi_app=self.dispatcher)

    def print_help_msg(self, host, port):
        if host == '0.0.0.0':
            sys.stdout.write(RUNNING_ON % ('localhost', port))
            for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
                if ip.startswith('192.'):
                    sys.stdout.write(RUNNING_ON % (ip, port))
                    break
        sys.stdout.write(HOW_TO_QUIT)


class RequestLogger(object):

    def __init__(self, application, **kw):
        self.application = application

    def log_request(self, environ, now=None):
        now = now or datetime.now()
        msg = [' ',
            now.strftime('%H:%M:%S'), ' | ',
            environ.get('REMOTE_ADDR', '?'), '  ',
            environ.get('REQUEST_URI', ''), '  ',
            '(', environ.get('REQUEST_METHOD', ''), ') \n',
            ]

        msg = ''.join(msg)
        sys.stdout.write(msg)

    def __call__(self, environ, start_response):
        self.log_request(environ)
        try:
            return self.application(environ, start_response)
        except Exception, e:
            start_response(HTTPMSG, [('Content-type', 'text/plain')], sys.exc_info())
            raise
