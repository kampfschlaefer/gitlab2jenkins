
from lxml import etree
from jenkinsapi import jenkins
from jenkinsapi.utils.requester import Requester
import json
import re

import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()

import logging
logger = logging.getLogger(__name__)

# This script connects Gitlab with Jenkins and automatically creates new
# Jenkins jobs from templates for new branches (currently only release
# branches, sprint branches and master).

JENKINS_URL = 'http://localhost'
JENKINS_USER = 'mr.jenkins'
JENKINS_APITOKEN = ''
JENKINS_DESCTEMPLATE = '''
Automatically created job for branch <i>%(branch)s</i>\n
of project <a href="%(uri)s">%(repo)s</a>.\n
Cloned from template <a href="/job/%(template)s">%(template)s</a>.

<strong>Do not edit this job!</strong>\nInstead,
<a href="/job/%(template)s/configure">edit the template job</a>.\n
Changes to the template will be propagated to all cloned jobs.
'''

j = None


def repo(data):
    ''' Get repo name from Gitlab JSON data. '''
    return data['repository']['name'].lower()


def branch(data):
    ''' Get branch name from Gitlab JSON data. '''
    ref = data['ref']
    if ref.startswith('refs/heads/'):
        return ref[11:]
    else:  # pragma: no cover
        # I have no idea if this can happen. Maybe raise an exception?
        logging.error('branch(%s) this should not be reached...', ref)
        return ref


def branch_created(data):  # pragma: no cover
    ''' Determine from JSON data if a new branch was created. '''
    return int(data['before'], base=16) == 0


def branch_deleted(data):
    ''' Determine from JSON data if a branch was deleted. '''
    return int(data['after'], base=16) == 0


def template_name(kind, data):
    ''' Get template name for this kind from JSON data. '''
    return 'template-%s-%s' % (kind, repo(data))


def job_name(kind, data):
    ''' Get the job name for this kind from JSON data. '''
    return '%s-%s-%s' % (kind, repo(data), branch(data).replace('/', '_'))


def set_branch(xml, bname):
    ''' Set the git branch in the given job config XML. '''
    for e in xml.iter(tag=etree.Element):
        if e.tag == 'hudson.plugins.git.BranchSpec':
            for child in e:
                if child.tag == 'name':
                    child.text = 'origin/%s' % bname


def gen_description(b, r, tn, data):
    ''' Generate a nice description for a job. '''
    subs = {
        'branch': b,
        'repo': r,
        'template': tn,
        'uri': data['repository']['homepage']
    }
    return JENKINS_DESCTEMPLATE % subs


def set_description(xml, desc):
    ''' Set the job description in the given job config XML. '''
    for child in xml:
        if child.tag == 'description':
            child.text = desc


def set_enabled(xml):
    ''' Set a job enabled in the given job config XML. '''
    for child in xml:
        if child.tag == 'disabled':
            child.text = 'false'


def view_for_job(job):
    ''' Determine the view that the given job is in. '''
    # logging.debug('all views: %s', ', '.join(j.views))
    # skip views for now
    return None
    for vname in j.views:  # pragma: no cover
        if vname in ['All', 'Alle']:
            continue
        view = j.views[vname]
        # logging.debug('view is %s', view)
        if view and job in view.get_job_dict():
            # logging.debug('found job %s in view %s', job, view)
            return view
    return None


def refresh(jenkins_url, user, apitoken, ssl_verify=True):
    ''' Reconnect to Jenkins, needed after creating new jobs. '''
    global j
    requester = Requester(
        username=user, password=apitoken,
        baseurl=jenkins_url, ssl_verify=ssl_verify
    )
    j = jenkins.Jenkins(jenkins_url, user, apitoken, requester=requester)


def create_job(jobname, template, repo, branch, data, options={}):
    ''' Create a new job. '''
    global j
    cfg = gen_config(jobname, template, repo, branch, data)
    newjob = j.create_job(jobname, cfg)
    refresh(
        JENKINS_URL, JENKINS_USER, JENKINS_APITOKEN,
        ssl_verify=options.get('ssl_verify', True)
    )
    v = view_for_job(template)
    if v:
        v.add_job(jobname, newjob)
    return newjob


def gen_config(jobname, template, repo, branch, data):
    ''' Generate an XML job config. '''
    global j
    xml = etree.fromstring(j.get_job(template).get_config().encode('utf-8'))
    set_branch(xml, branch)
    set_enabled(xml)
    set_description(xml, gen_description(branch, repo, template, data))
    return etree.tostring(xml, pretty_print=True)


def handler(data, start_response, options={}):
    ''' The actual request handler. '''
    global j
    start_response('200 OK', [('Content-Type', 'text/html')])
    # see https://gitlab/help/web_hooks
    requestdata = data
    logger.debug('request data is %s\n', requestdata)
    logger.warning('ssl_verify is %s', options.get('ssl_verify'))
    data = json.loads(requestdata)
    r = repo(data)
    b = branch(data)
    refresh(
        JENKINS_URL, JENKINS_USER, JENKINS_APITOKEN,
        ssl_verify=options.get('ssl_verify', True)
    )
    # all_jobs = j.get_jobs()
    # all_views = j.views

    if (
        not re.match(r'^r[0-9\.]+(|-s.+)$', b) and
        not b.startswith('release-') and
        not b.startswith('master-') and
        not b == 'master'
    ):
        logger.info(
            'Branch in neither release, sprint nor story branch %s in repo %s.'
            ' Ignoring.\n' % (b, r)
        )
        return []

    kinds = ['ci']
    if re.match(r'^r[0-9\.]+(|-s[0-9_]+)$', b):
        kinds.append('nightly')

    logger.info("Handling incoming data: %r\n" % data)
    logger.info("Extracted: repo %s, branch %s\n" % (r, b))

    # We have two kinds of jobs, ci (continuous integration) and nightly.
    for kind in kinds:
        tn = template_name(kind, data)
        jn = job_name(kind, data)
        logger.info("Will work with template %s, job %s\n" % (tn, jn))

        if not j.has_job(tn):
            # If we don't have a template, there is nothing we can do anyways
            continue

        if False and branch_created(data):  # pragma: no cover
            res = "Registered new branch %s in repo %s\n" % (b, r)
            logger.info(res)
            job = create_job(jn, tn, r, b, data, options)
            if kind != 'nightly':
                logger.info('Will invoke this %s job directly.', kind)
                job.invoke()

        elif branch_deleted(data):
            res = "Registered deleted branch %s in repo %s\n" % (b, r)
            logger.info(res)
            if j.has_job(jn):
                j.delete_job(jn)
        else:  # Just a regular commit on an existing branch.
            res = "Registered commit to %s on branch %s\n" % (r, b)
            logger.info(res)
            if not j.has_job(jn):
                job = create_job(jn, tn, r, b, data, options)
            else:
                job = j.get_job(jn)
                job.update_config(gen_config(jn, tn, r, b, data))
            if kind != 'nightly':
                logger.info('Will invoke this %s job.', kind)
                job.invoke()

    return []
