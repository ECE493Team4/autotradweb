############
autotradeweb
############

.. image:: https://travis-ci.com/ECE493Team4/autotradweb.svg?branch=master
    :target: https://travis-ci.com/ECE493Team4/autotradweb
    :alt: Build Status

Description
===========

Front end web server for autotrader capstone project.

Installation
============

To install autotradeweb and its dependencies within your local python
environment run the following command within the autotradeweb project
directory containing ``setup.py``:

.. code-block:: console

    pip install .

Usage
=====

To get help on starting up autotradeweb run the following command:

.. code-block:: console

    autotradeweb --help


Testing
=======

Unit/Instrumentation Testing
----------------------------

To run unit and instrumentation testing for autotradeweb you must have a valid
database URI to the remote autotradeweb PostgreSQL test database. Afterwards,
you must set the environment ``TEST_DATABASE_URI`` variable with this URI:

.. code-block:: console

    TEST_DATABASE_URI=<your database URI to the remote autotradeweb PostgreSQL test database>

After, setting this environment variable you can run the pytest suite for
autotradeweb fully with the following command:

.. code-block:: console

    python setup.py test

Static Analysis
---------------

To run static analysis testing over autotradeweb with pylint run the following
command:

.. code-block:: console

    python setup.py lint
