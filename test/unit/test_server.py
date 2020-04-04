#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""pytests for :mod:`.server`"""

import os
from datetime import datetime

import pytest
from sqlalchemy.exc import OperationalError

from autotradeweb.server import APP, User, db, trading_session, trade, stock_prediction, \
    stock_data

# NOTE: to run these tests you must set a enviroment variable witht the database URI
# of autotradeweb postgresql test database
APP.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('TEST_DATABASE_URI')


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
        # setup empty the user table
        db.session.query(User).delete()
        db.session.commit()

        try:
            resp = client.post("/register", data={"email": "foo", "psw": 'bar'})
            assert resp.status_code == 302
            assert "login" in resp.location
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


class TestDatabaseBindings:

    def test_add_user(self):
        db.session.query(User).delete()
        db.session.commit()
        user = User(username="foo", password="bar")
        db.session.add(user)
        db.session.commit()
        assert user.id
        assert user.to_dict()

    def test_add_trading_session(self):
        trading_session_ = trading_session(username="foo", ticker="bar", start_time=datetime.now())
        db.session.add(trading_session_)
        db.session.commit()
        assert trading_session_.session_id
        assert trading_session_.to_dict()
        db.session.delete(trading_session_)
        db.session.commit()

    def test_get_trade(self):
        trade_ = db.session.query(trade).first()
        assert trade_
        assert trade_.trade_id
        assert trade_.to_dict()

    def test_get_stock_prediction(self):
        stock_prediction_ = db.session.query(stock_prediction).first()
        assert stock_prediction_
        assert stock_prediction_.stock_name

    def test_get_stock_data(self):
        stock_data_ = db.session.query(stock_data).first()
        assert stock_data_
        assert stock_data_.stock_name
