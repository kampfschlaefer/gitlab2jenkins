
# import os
import sys
from setuptools import setup, find_packages, Command
# from distutils.command.build_py import build_py
# from subprocess import call, PIPE


class PyTest(Command):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        self.pytest_args = [
            '-v',
            '--cov', 'mcp', '--cov', 'tests',
            '--cov-report', 'html', '--cov-report', 'xml'
        ]

    def finalize_options(self):
        pass

    def run(self):
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
    tests_require=[
        'pytest',
        'pytest-localserver'
    ],
    requires=[
        'gevent',
    ]
)
