#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""autotradeweb setup.py"""

import codecs
import os
import re
import sys

from setuptools import setup, find_packages
from setuptools.command.test import test


def find_version(*file_paths):
    with codecs.open(
        os.path.join(os.path.abspath(os.path.dirname(__file__)), *file_paths), "r"
    ) as fp:
        version_file = fp.read()
    m = re.search(r"^__version__ = \((\d+), ?(\d+), ?(\d+)\)", version_file, re.M)
    if m:
        return "{}.{}.{}".format(*m.groups())
    raise RuntimeError("Unable to find a valid version")


VERSION = find_version("autotradeweb", "__init__.py")


class Pylint(test):
    user_options = [("pylint-args=", "a", "Arguments to pass to pylint")]

    def initialize_options(self):
        test.initialize_options(self)
        self.pylint_args = (
            "autotradeweb --persistent=y --rcfile=.pylintrc --output-format=colorized"
        )

    def run_tests(self):
        import shlex

        # import here, cause outside the eggs aren't loaded
        from pylint.lint import Run

        Run(shlex.split(self.pylint_args))


class PyTest(test):
    user_options = [("pytest-args=", "a", "Arguments to pass to pytest")]

    def initialize_options(self):
        test.initialize_options(self)
        self.pytest_args = "-v --cov={}".format("autotradeweb")

    def run_tests(self):
        import shlex

        # import here, cause outside the eggs aren't loaded
        import pytest

        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


def readme():
    with open("README.rst", encoding="utf-8") as f:
        return f.read()


setup(
    name="autotradeweb",
    version=VERSION,
    description="Front end web server for autotrader capstone project.",
    long_description=readme(),
    author="Nathan Klapstein",
    author_email="nklapste@ualberta.ca",
    url="https://github.com/ECE493Team4/autotradweb",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    packages=find_packages(exclude=["test"]),
    include_package_data=True,
    install_requires=[
        "cheroot>=8.3.0,<9.0.0",
        "flask>=1.1.1,<2.0.0",
        "flask-sqlalchemy>=2.4.1,<3.0.0",
        "flask-simplelogin>=0.0.7,<1.0.0",
        "flask-restx>=0.2.0,<1.0.0",
        "dash>=1.9.1,<2.0.0",
        "dash-html-components>=1.0.2,<2.0.0",
        "dash-core-components>=1.8.1,<2.0.0",
        "dash-table>=4.6.1,<5.0.0",
        "psycopg2-binary>=2.8.4,<3.0.0",
        "graypy>=2.1.0,<3.0.0",
    ],
    tests_require=[
        "pytest>=4.1.0,<5.0.0",
        "pytest-cov>=2.6.1,<3.0.0",
        "pylint>=2.2.2,<3.0.0",
        "beautifulsoup4>=4.8.2,<5.0.0",
        # "dash[testing]>=1.9.1,<2.0.0",
    ],
    entry_points={"console_scripts": ["autotradeweb = autotradeweb.__main__:main"]},
    cmdclass={"test": PyTest, "lint": Pylint},
)
