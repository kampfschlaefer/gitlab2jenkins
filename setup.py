
# import os
import sys
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
# from distutils.command.build_py import build_py
# from subprocess import call, PIPE


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = [
            '-v',
            '--cov', 'gitlabtojenkins',
            '--cov-report', 'html', '--cov-report', 'xml'
        ]

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name='gitlab2jenkins',
    version='0.1',
    description='gateprotect gitlab-to-jenkins webhook',
    author='Arnold Krille',
    author_email='developers@gateprotect.com',
    url='http://www.gateprotect.com',
    packages=find_packages(),
    cmdclass={
        'test': PyTest,
    },
    setup_requires=['setuptools>=7.0'],
    tests_require=[
        'pytest==2.7.0',
        'pytest-localserver==0.3.4',
        'pytest-cov==1.8.1'
    ],
    install_requires=[
        'jenkinsapi==0.2.26',
        'lxml==3.4.2',
        #  'gevent',
    ]
)
