
from gevent.pywsgi import WSGIServer

from .handler import handler


def application(env, start_response):
    if env['PATH_INFO'] == '/':
        # print env
        if env['REQUEST_METHOD'] == 'POST':
            # start_response('200 OK', [])
            length = int(env.get('CONTENT_LENGTH', 0))
            return handler(env['wsgi.input'].read(length), start_response)
        else:
            start_response('200 OK', [('Content-Type', 'text/html')])
            return [
                '<h1>It worked</h1>',
                '<p>But to use me, you have to POST gitlab information.</p>'
            ]
    else:
        start_response('404 Not Found', [('Content-Type', 'text/html')])
        return [
            '<h1>Not found</h1>',
            '<p>The path %s was not found</p>' % env['PATH_INFO']
        ]


def run():
    print('running wsgi-server on port 8080')
    WSGIServer(('', 8080), application).serve_forever()
    print('done.')
