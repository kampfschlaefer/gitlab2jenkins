
import logging
logger = logging.getLogger(__name__)


def server_url(env, path=''):
    return '%s://%s:%s%s' % (
        env['wsgi.url_scheme'],
        env['SERVER_NAME'],
        env['SERVER_PORT'],
        path  # .strip('/')
    )


def get_jobs(env, start_response):
    start_response('200 OK', [])
    return [
        open('tests/example_data/get_jobs.py', 'r').read() % {
            'server': server_url(env)
        }
    ]


def get_diaspora_ci_template(env, start_response):
    start_response('200 OK', [])
    return [
        open('tests/example_data/get_diaspora_ci_template.py', 'r').read() % {
            'server': server_url(env)
        }
    ]


def default_handler(env, start_response):
    logger.warning('Got unhandled request %s' % env)
    length = int(env.get('Content-Length', 0))
    logger.warning('Data sent was %s' % env['wsgi.input'].read(length))
    start_response('500 Server Error', [])
    return ['Default handler reached']


handlers = {
    ('/api/python', 'GET'): get_jobs,
    ('/job/template-ci-diaspora/api/python', 'GET'): get_diaspora_ci_template,
    ('/api/python', 'POST'): default_handler,
}


def jenkins_app(env, start_response):
    # logger.debug('got request with %s' % env)
    path = env['PATH_INFO']
    method = env['REQUEST_METHOD']
    handler = handlers.get((path, method), default_handler)
    ret = handler(env, start_response)
    logger.debug('Will answer with %s', ret)
    return ret
