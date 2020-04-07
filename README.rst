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

Development Usage
------------------

To start autotradeweb in a debugging instance connected to a remote testing
PostgreSQL database specified by the URI ``TEST_DATABASE_URI`` run the
following command:

.. code-block:: console

    autotradeweb --debug --verbose -d 127.0.0.1 -p 8999 --database <TEST_DATABASE_URI> --disable-https

Afterwards, you should be able to access the autotradeweb web service
at http://127.0.0.1:8999/

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
