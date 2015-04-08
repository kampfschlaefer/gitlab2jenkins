
from gevent.pywsgi import WSGIServer
from gevent import monkey
monkey.patch_all()

import ConfigParser
import os.path

from gitlabtojenkins import handler

import logging
logger = logging.getLogger(__name__)


def parse_config(filenames):
    config = ConfigParser.SafeConfigParser()
    config.add_section('gitlab2jenkins')
    config.set('gitlab2jenkins', 'jenkins_url', 'http://localhost')
    config.set('gitlab2jenkins', 'jenkins_user', 'mr.jenkins')
    config.set('gitlab2jenkins', 'jenkins_apitoken', 'notset')
    config.read(filenames)
    handler.JENKINS_URL = config.get('gitlab2jenkins', 'jenkins_url')
    handler.JENKINS_USER = config.get('gitlab2jenkins', 'jenkins_user')
    handler.JENKINS_APITOKEN = config.get('gitlab2jenkins', 'jenkins_apitoken')


def application(env, start_response):
    if env['PATH_INFO'] == '/':
        if env['REQUEST_METHOD'] == 'POST':
            length = int(env.get('CONTENT_LENGTH', 0))
            return handler.handler(
                env['wsgi.input'].read(length),
                start_response
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
    logger.info(
        'Reading config from (in order):\n'
        '  /etc/gitlab2jenkins.conf\n'
        '  ~/.gitlab2jenkins.conf\n'
        '  .gitlab2jenkins.conf'
    )
    parse_config(
        [
            '/etc/gitlab2jenkins.conf',
            os.path.expanduser('~/.gitlab2jenkins.conf'),
            '.gitlab2jenkins.conf'
        ]
    )
    logger.info('running wsgi-server on port 8080')
    WSGIServer(('', 8080), application).serve_forever()
    logger.info('done.')
