
from gevent.pywsgi import WSGIServer
from gevent import monkey
monkey.patch_all()

import ConfigParser
import os.path
import os

from gitlabtojenkins import handler

import logging
logging.captureWarnings(True)
logger = logging.getLogger(__name__)

options = {}


def parse_config(filenames):
    global options
    config = ConfigParser.SafeConfigParser()
    config.add_section('gitlab2jenkins')
    config.set('gitlab2jenkins', 'jenkins_url', 'http://localhost')
    config.set('gitlab2jenkins', 'jenkins_user', 'mr.jenkins')
    config.set('gitlab2jenkins', 'jenkins_apitoken', 'notset')
    config.set('gitlab2jenkins', 'listen', '0.0.0.0')
    config.set('gitlab2jenkins', 'port', '8080')
    config.set('gitlab2jenkins', 'ssl_verify', 'True')
    logger.info('parsed configs from %s', config.read(filenames))
    handler.JENKINS_URL = config.get('gitlab2jenkins', 'jenkins_url')
    handler.JENKINS_USER = config.get('gitlab2jenkins', 'jenkins_user')
    handler.JENKINS_APITOKEN = config.get('gitlab2jenkins', 'jenkins_apitoken')
    options['ssl_verify'] = config.get('gitlab2jenkins', 'ssl_verify') == True
    return config


def application(env, start_response):
    global options
    logger.debug('env = %s', env)
    if env['PATH_INFO'] == '/':
        if env['REQUEST_METHOD'] == 'POST':
            length = int(env.get('CONTENT_LENGTH', 0))
            return handler.handler(
                env['wsgi.input'].read(length),
                start_response,
                options=options
            )
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
    logging.basicConfig(level=logging.INFO)
    config_paths = [
        '/etc/gitlab2jenkins.conf',
        os.path.expanduser('~/.gitlab2jenkins.conf'),
        '.gitlab2jenkins.conf'
    ]
    logger.info(
        'Reading config from (in order):\n%s' % '\n'.join(config_paths)
    )
    config = parse_config(config_paths)
    logger.info(
        'running wsgi-server on port %s',
        config.getint('gitlab2jenkins', 'port')
    )
    logger.info(' CWD is %s', os.getcwd())
    WSGIServer(
        (
            config.get('gitlab2jenkins', 'listen'),
            config.getint('gitlab2jenkins', 'port')
        ),
        application,
    ).serve_forever()
    logger.info('done.')
