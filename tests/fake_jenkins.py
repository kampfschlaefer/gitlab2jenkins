
import pprint
import re
import copy

import logging
logger = logging.getLogger(__name__)

job_template = {
    "actions": [{}, {}, {}, {}, {}],
    "description": "Template for testing continuous integration tests.",
    "displayName": None,
    "displayNameOrNull": None,
    "name": None,
    "url": None,
    "buildable": False,
    "builds": [],
    "color": "disabled",
    "firstBuild": None,
    "healthReport": [],
    "inQueue": False,
    "keepDependencies": False,
    "lastBuild": None,
    "lastCompletedBuild": None,
    "lastFailedBuild": None,
    "lastStableBuild": None,
    "lastSuccessfulBuild": None,
    "lastUnstableBuild": None,
    "lastUnsuccessfulBuild": None,
    "nextBuildNumber": 1,
    "property": [
        {}, {},
        {
            "wallDisplayBgPicture": None,
            "wallDisplayName": None
        },
        {
            "children": [{}]
        }
    ],
    "queueItem": None,
    "concurrentBuild": False,
    "downstreamProjects": [],
    "scm": {},
    "upstreamProjects": []
}

jobs = {
    'template-ci-diaspora': {
        'color': 'disabled',
        'content': open(
            'tests/example_data/get_diaspora_ci_template.py', 'r'
        ).read(),
        'config': open(
            'tests/example_data/get_diaspora_config.xml', 'r'
        ).read()
    },
}

last_triggered_job = None


def server_url(env, path=''):
    return '%s://%s:%s%s' % (
        env['wsgi.url_scheme'],
        env['SERVER_NAME'],
        env['SERVER_PORT'],
        path
    )


def get_jobs(env, start_response):
    start_response('200 OK', [])
    ret = {
        'description': None,
        'jobs': [],
        'name': 'All',
        'property': [],
        'url': server_url(env)
    }
    for name, j in jobs.iteritems():
        ret['jobs'].append({
            'name': name,
            'url': server_url(env, '/job/%s' % name),
            'color': j['color']
        })
    return [
        pprint.pformat(ret, indent=4)
    ]


def get_job(env, start_response):
    start_response('200 OK', [])
    # logger.info('get job!')
    name = re.findall('/job/([^/]+)/api/python', env['PATH_INFO'])[0]
    logger.info('Searching for job %s', name)
    print 'Searching for job %s' % name
    content = jobs[name]['content']
    print "\"%s\"" % content
    # logger.info(' Jobs content is %s', content)
    return [content]


def get_diaspora_config_xml(env, start_response):
    start_response('200 OK', [])
    return [open('tests/example_data/get_diaspora_config.xml', 'r').read()]


def post_new_job(env, start_response):
    logger.debug('env is %s', env)
    start_response('200 Created', [])
    query = env.get('QUERY_STRING', '')
    name = None
    if query:
        for q in query.split('&'):
            k, v = q.split('=')
            if k == 'name':
                name = v
    datalength = int(env.get('CONTENT_LENGTH', 0))
    data = env['wsgi.input'].read(datalength)
    # logger.info('Posted data "%s"', data)
    newjob = copy.deepcopy(job_template)
    newjob['name'] = name
    newjob['url'] = server_url(env, '/job/%s/' % name)
    # logger.info('newjob = %s', pprint.pformat(newjob, indent=4))
    if name:
        jobs[name] = {
            'color': 'blue',
            'content': pprint.pformat(newjob, indent=4),
            'config': data,
        }
    logger.info('Creating job with name \'%s\'', name)
    return []


def post_build_job(env, start_response):
    global last_triggered_job
    job = re.findall('/job/([^/]+)/build', env['PATH_INFO'])[0]
    logger.info('Build job "%s"!', job)
    start_response(
        '201 Created', [
            ('Location', server_url(env, '/queue/item/1/'))
        ]
    )
    last_triggered_job = job
    return []


def get_queue_details(env, start_response):
    build_id = int(
        re.findall('/queue/item/(\d+)/api/python', env['PATH_INFO'])[0]
    )
    ret = """
{
    "actions":[
        {
            "causes":[
                {
                    "shortDescription":"Started by user Arnold Krille",
                    "userId":"arnold.krille",
                    "userName":"Arnold Krille"
                }
            ]
        },
        {}
    ],
    "blocked":False,
    "buildable":False,
    "id":%(build_id)s,
    "inQueueSince":14277904127%(build_id)02i,
    "params":"",
    "stuck":False,
    "task":{
        "name":"%(job)s",
        "url":"%(server)s/job/%(job)s/",
        "color":"blue"
    },
    "url":"queue/item/5/",
    "why":None,
    "cancelled":False,
    "executable":{
        "number":12,
        "url":"%(server)s/job/%(job)s/"
    }
}""" % {
        'job': last_triggered_job,
        'build_id': build_id,
        'server': server_url(env),
    }

    start_response("200 OK", [])
    return [ret]


def default_handler(env, start_response):
    print 'unhandled request to %s' % env['PATH_INFO']
    logger.warning('Got unhandled request %s' % env)
    length = int(env.get('CONTENT_LENGTH', 0))
    logger.warning('Data sent was %s' % env['wsgi.input'].read(length))
    start_response('500 Server Error', [])
    return ['Default handler reached']


handlers = {
    ('/api/python', 'GET'): get_jobs,
    ('/createItem', 'POST'): post_new_job,
    (r'/job/[^/]+/api/python', 'GET'): get_job,
    ('/job/template-ci-diaspora/config.xml', 'GET'): get_diaspora_config_xml,
    (r'/job/[^/]+/build', 'POST'): post_build_job,
    (r'/queue/item/[\d]+/api/python', 'GET'): get_queue_details,
}


def jenkins_app(env, start_response):
    # logger.debug('got request with %s' % env)
    path = env['PATH_INFO']
    method = env['REQUEST_METHOD']
    handler = default_handler
    for pathmatcher, methodmatcher in handlers:
        logger.info(
            'matching %s %s to %s %s',
            method, path, methodmatcher, pathmatcher
        )
        if methodmatcher == method and re.match(pathmatcher, path):
            handler = handlers.get((pathmatcher, methodmatcher))
            break
    logger.debug('handler = %s', handler)
    ret = handler(env, start_response)
    # logger.debug('Will answer with %s', ret)
    return ret
