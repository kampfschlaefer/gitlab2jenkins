
from pytest_localserver.http import WSGIServer
import pytest
import requests

import gitlabtojenkins.handler

from jenkins_api_simulator.statefull import app as jenkins_app
from jenkinsapi import jenkins
from gitlabtojenkins.server import application


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


def test_invalid_url(testserver):
    r = requests.get('%s/invalid' % testserver.url)
    assert r.status_code == 404
    assert 'Not found' in r.text, r.text


def test_get_valid_url(testserver):
    r = requests.get(testserver.url)
    assert r.status_code == 200
    assert 'worked' in r.text


def test_example_push_event_no_templates(testserver, fake_jenkins, example_push):
    gitlabtojenkins.handler.JENKINS_URL = fake_jenkins.url
    r = requests.post(testserver.url, example_push)
    assert r.status_code == 200
    assert r.text == ''

    j = jenkins.Jenkins(fake_jenkins.url)
    assert not j.keys()


def test_example_push_event_ci_template(testserver, fake_jenkins, example_push):
    j = jenkins.Jenkins(fake_jenkins.url)
    j.create_job(
        'template-ci-diaspora',
        open('tests/example_data/get_diaspora_config.xml', 'r').read()
    )

    gitlabtojenkins.handler.JENKINS_URL = fake_jenkins.url
    r = requests.post(testserver.url, example_push)
    assert r.status_code == 200
    assert r.text == ''

    j = jenkins.Jenkins(fake_jenkins.url)
    jobs = j.keys()
    assert 'template-ci-diaspora' in jobs
    assert 'ci-diaspora-master' in jobs
