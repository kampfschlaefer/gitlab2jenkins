
from gevent import monkey
monkey.patch_all()

from pytest_localserver.http import WSGIServer
import tempfile
import pytest
import requests
import gevent
import random
import logging
import socket

import gitlabtojenkins.handler

from jenkins_api_simulator.statefull import app as jenkins_app
from jenkinsapi import jenkins
from jenkinsapi.utils.requester import Requester
from gitlabtojenkins.server import application, parse_config, run


@pytest.yield_fixture
def testserver():
    server = WSGIServer(application=application)
    server.start()
    yield server
    server.stop()


@pytest.yield_fixture
def fake_jenkins():
    # FIXME Sadly gevent1.0.1 together with python 2.7.9+ have a problem with running ssl servers.
    # jenkins_server = WSGIServer(application=jenkins_app, ssl_context='adhoc')
    jenkins_server = WSGIServer(application=jenkins_app)
    jenkins_server.start()
    yield jenkins_server
    jenkins_server.stop()


@pytest.fixture
def requester_factory(fake_jenkins):
    url = fake_jenkins.url

    def factory():
        return Requester(
            username=None, password=None,
            baseurl=url, ssl_verify=False
        )

    return factory


@pytest.fixture
def example_push():
    return open('tests/example_data/push_event.json').read()


def prepare_config(
    tmpdir, jenkins_url, jenkins_user=None, jenkins_apitoken=None
):
    f = tempfile.NamedTemporaryFile(dir=str(tmpdir))
    f.file.write('[gitlab2jenkins]\n')
    f.file.write('ssl_verify = False\n')
    f.file.write('jenkins_url = %s\n' % jenkins_url)
    if jenkins_user:
        f.file.write('jenkins_user = %s\n' % jenkins_user)
    if jenkins_apitoken:
        f.file.write('jenkins_apitoken = %s\n' % jenkins_apitoken)
    f.file.flush()
    return f


def test_invalid_url(testserver):
    r = requests.get('%s/invalid' % testserver.url)
    assert r.status_code == 404
    assert 'Not found' in r.text, r.text


def test_get_valid_url(testserver):
    r = requests.get(testserver.url)
    assert r.status_code == 200
    assert 'worked' in r.text


def test_parse_config(tmpdir):
    f = prepare_config(
        tmpdir,
        jenkins_url='http://jenkins.example.com',
        jenkins_user='jenkins',
        jenkins_apitoken='superdupersecrettoken'
    )
    parse_config(filenames=[f.name])
    assert gitlabtojenkins.handler.JENKINS_URL == 'http://jenkins.example.com'
    assert gitlabtojenkins.handler.JENKINS_USER == 'jenkins'
    assert gitlabtojenkins.handler.JENKINS_APITOKEN == 'superdupersecrettoken'


def test_parse_config_not_existing():
    parse_config(filenames=['/tmp/bla/not_existing'])
    assert gitlabtojenkins.handler.JENKINS_URL == 'http://localhost'


def test_example_push_no_templates(
    tmpdir, testserver, fake_jenkins, requester_factory, example_push
):
    configfile = prepare_config(tmpdir, jenkins_url=fake_jenkins.url)
    parse_config([configfile.name])
    r = requests.post(testserver.url, example_push)
    assert r.status_code == 200
    assert r.text == ''

    j = jenkins.Jenkins(fake_jenkins.url, requester=requester_factory())
    assert not j.keys()


def test_example_push_ci_template(
    tmpdir, testserver, fake_jenkins, requester_factory, example_push
):
    j = jenkins.Jenkins(fake_jenkins.url, requester=requester_factory())
    j.create_job(
        'template-ci-diaspora',
        open('tests/example_data/get_diaspora_config.xml', 'r').read()
    )

    configfile = prepare_config(tmpdir, jenkins_url=fake_jenkins.url)
    parse_config([configfile.name])
    r = requests.post(testserver.url, example_push)
    assert r.status_code == 200
    assert r.text == ''

    j = jenkins.Jenkins(fake_jenkins.url, requester=requester_factory())
    jobs = j.keys()
    assert 'template-ci-diaspora' in jobs
    assert 'ci-diaspora-master' in jobs


class TestStandaloneApplication(object):
    def test_run_with_defaults(self, tmpdir, fake_jenkins, example_push):
        configfile = tmpdir.join('.gitlab2jenkins.conf')
        with configfile.open('w') as f:
            f.write('[gitlab2jenkins]\njenkins_url = %s\n' % fake_jenkins.url)

        with tmpdir.as_cwd():
            g = gevent.Greenlet(run)
            g.start()
            gevent.sleep(0.1)

        r = requests.get('http://localhost:8080/')
        assert r.status_code == 200

        gevent.sleep(0.1)
        g.kill()
        g.join()

        assert g.exception is None

    def test_run_on_localhost_custom_port(
        self, tmpdir, fake_jenkins, example_push
    ):
        custom_port = random.randint(8000, 9000)
        logging.info('Will try to run with port %s', custom_port)
        configfile = tmpdir.join('.gitlab2jenkins.conf')
        with configfile.open('w') as f:
            f.write(
                '[gitlab2jenkins]\njenkins_url = %s\n'
                'listen = 127.0.0.1\nport = %i\n' % (
                    fake_jenkins.url,
                    custom_port
                )
            )

        with tmpdir.as_cwd():
            g = gevent.Greenlet(run)
            g.start()
            gevent.sleep(0.1)

        r = requests.get('http://localhost:%s/' % custom_port)
        assert r.status_code == 200

        with pytest.raises(requests.ConnectionError):
            r = requests.get('http://localhost:8080/')
            assert r.status_code != 200

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.4.4', 80))
        localip = s.getsockname()[0]
        logging.info(' Local socket %s', localip)
        s.close()
        with pytest.raises(requests.ConnectionError):
            r = requests.get('http://%s:%s/' % (localip, custom_port))
            assert r.status_code != 200

        gevent.sleep(0.1)
        g.kill()
        g.join()

        assert g.exception is None
