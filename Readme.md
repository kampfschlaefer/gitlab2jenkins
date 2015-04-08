# gitlab2jenkins

This is the new webhook to connect gitlab with jenkins the way we want it.

## What does it do?

We want jenkins-jobs per story-, sprint- and release-branch without configuring them manually. And we don't want only one story-job that checks all stories sequentially, we want one job per story to keep track of the success within this story.

So this is a small service to get one push-event as webhook from gitlab and translates to a number of requests against jenkins to:

- when the branch name doesn't match the naming conventions, it does nothing,
- when there is no template matching 'template-*repo*-(ci|nightly)' it does nothing, otherwise
- when there is no job for this branch, it creates the job
- it copies the template, replaces the branch specifier and set this as new config for the job
- if its a ci-job, it triggers the execution

- when the push-event deletes a branch, it deletes the job too

## How to deploy?

From github tarball:
```shell
$> pip install https://github.com/GateprotectGmbH/gitlab2jenkins/tarball/master-s13_14-46227#egg=gitlab2jenkins-0.1
```

The configuration is read from `/etc/gitlab2jenkins.conf`, `~/.gitlab2jenkins.conf` and `.gitlab2jenkins.conf`. The files are tried in that order, settings in the later overwrite the files before. The config looks like this:

```ini
[gitlab2jenkins]
jenkins_url = http://localhost:8080
jenkins_user = mr.jenkins
jenkins_apitoken = jenkinssecretapitoken
```

## How to run?

Run the installed executable `gitlab2jenkins_server`. This runs it own small wsgi server on http://0.0.0.0:8080 and listens for events from gitlab.
Add it to your projects webhooks in gitlab with the url.

The server should be run as daemon from some kind of init-system to start automatically and restart when needed. Also you can (should?) proxy this service with apache or nginx if you want to run it on a different port.

## What more is to come?

This project has issues. It could be more configurable, easier deployable, more extendable. Add your thoughts [here on the github issues](https://github.com/GateprotectGmbH/gitlab2jenkins/issues).