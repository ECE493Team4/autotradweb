#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""pytests for :mod:`.server`"""

import pytest

from autotradeweb.server import APP


@pytest.fixture(scope='module')
def client():
    """init the autotradeweb flask app as a testing client"""
    flask_app = APP
    flask_app.config['DEBUG'] = True
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


class TestCase:
    def test_index(self, client):
        resp = client.get("/")
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
