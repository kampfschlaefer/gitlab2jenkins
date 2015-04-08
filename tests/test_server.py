
from pytest_localserver.http import WSGIServer
import tempfile
import pytest
import requests

import gitlabtojenkins.handler

from jenkins_api_simulator.statefull import app as jenkins_app
from jenkinsapi import jenkins
from gitlabtojenkins.server import application, parse_config


@pytest.yield_fixture
def testserver():
    server = WSGIServer(application=application)
    server.start()
    yield server
    server.stop()


@pytest.yield_fixture
def fake_jenkins():
    jenkins = WSGIServer(application=jenkins_app)
    jenkins.start()
    yield jenkins
    jenkins.stop()


@pytest.fixture
def example_push():
    return open('tests/example_data/push_event.json').read()


def prepare_config(tmpdir, jenkins_url, jenkins_user=None, jenkins_apitoken=None):
    f = tempfile.NamedTemporaryFile(dir=str(tmpdir))
    f.file.write('[gitlab2jenkins]\njenkins_url = %s\n' % jenkins_url)
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


def test_example_push_no_templates(tmpdir, testserver, fake_jenkins, example_push):
    configfile = prepare_config(tmpdir, jenkins_url=fake_jenkins.url)
    parse_config([configfile.name])
    r = requests.post(testserver.url, example_push)
    assert r.status_code == 200
    assert r.text == ''

    j = jenkins.Jenkins(fake_jenkins.url)
    assert not j.keys()


def test_example_push_ci_template(tmpdir, testserver, fake_jenkins, example_push):
    j = jenkins.Jenkins(fake_jenkins.url)
    j.create_job(
        'template-ci-diaspora',
        open('tests/example_data/get_diaspora_config.xml', 'r').read()
    )

    configfile = prepare_config(tmpdir, jenkins_url=fake_jenkins.url)
    parse_config([configfile.name])
    r = requests.post(testserver.url, example_push)
    assert r.status_code == 200
    assert r.text == ''

    j = jenkins.Jenkins(fake_jenkins.url)
    jobs = j.keys()
    assert 'template-ci-diaspora' in jobs
    assert 'ci-diaspora-master' in jobs
