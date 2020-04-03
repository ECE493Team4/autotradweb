#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""pytests for :mod:`.server`"""

import pytest
from sqlalchemy.exc import OperationalError

from autotradeweb.server import APP


@pytest.fixture(scope='module')
def client():
    """init the autotradeweb flask app as a testing client"""
    flask_app = APP
    flask_app.config['DEBUG'] = True
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


class TestBasicFlaskApp:

    def test_index(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_register(self, client):
        resp = client.get("/register")
        assert resp.status_code == 200

    def test_api(self, client):
        resp = client.get("/api")
        assert resp.status_code == 200

    @pytest.mark.parametrize("page", ["/account", "/history", "/dashboard"])
    def test_account_no_login(self, client, page):
        """test that browsing to the account page while logged out
        redirects the user to the login page"""
        resp = client.get(page)
        assert resp.status_code == 302
        assert "login" in resp.location

    def test_register(self, client):
        resp = client.get("/register")
        assert resp.status_code == 200

    def test_register_post(self, client):
        # TODO: does not work until we find way to emulate postgrelocally
        try:
            resp = client.post("/register", data={"email": "foo", "psw": 'bar'})
            assert resp.status_code == 200
        except OperationalError:
            pass


@pytest.fixture(scope='module')
def logged_in_client(client):
    """init the autotradeweb flask app as a testing client"""
    yield client


class TestLoggedInBasicFlaskApp:
    @pytest.mark.parametrize("page", ["/account", "/history", "/dashboard"])
    def test_account_no_login(self, logged_in_client, page):
        """test that browsing to the account page while logged in goes on
        as intended"""
        # TODO: implement
        assert False
