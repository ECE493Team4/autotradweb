#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""pytests for :mod:`.server`"""

import json
import os
from datetime import datetime

import pytest
from sqlalchemy.exc import OperationalError
from bs4 import BeautifulSoup

from autotradeweb.server import APP, User, db, trading_session, trade, stock_prediction, \
    stock_data

# NOTE: to run these tests you must set a enviroment variable witht the database URI
# of autotradeweb postgresql test database
APP.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('TEST_DATABASE_URI')


def clear_user_related_db_entities():
    db.session.query(trade).delete()
    db.session.query(trading_session).delete()
    db.session.query(User).delete()
    db.session.commit()


def teardown_module(module):
    """ teardown any state that was previously setup with a setup_module
    method.
    """
    clear_user_related_db_entities()


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
    def test_page_no_login(self, client, page):
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

    def test_login(self, client):
        """register a user and attempt a login"""
        # setup empty the user table
        db.session.query(User).delete()
        db.session.commit()

        try:
            resp = client.post("/register", data={"email": "foo", "psw": 'bar'})
            assert resp.status_code == 302
            assert "login" in resp.location
        except OperationalError:
            pass

        resp = client.get("/login/")
        print(resp.location)
        soup = BeautifulSoup(resp.data, 'html.parser')
        csrf_token = soup.find(id="csrf_token")["value"]

        print(csrf_token)
        resp = client.post(
            "/login/",
            data=dict(
                username="foo",
                password="bar",
                next="/",
                csrf_token=csrf_token
            ),
            follow_redirects=True
        )
        assert resp.status_code == 200

        resp = client.get(
            "/account",
        )
        assert resp.status_code == 200
        resp = client.get(
            "/logout/",
        )
        assert resp.status_code == 302


@pytest.fixture(scope='module')
def logged_in_client(client):
    """init the autotradeweb flask app as a testing client"""
    db.session.query(User).delete()
    db.session.commit()

    try:
        resp = client.post("/register", data={"email": "foo", "psw": 'bar'})
        assert resp.status_code == 302
        assert "login" in resp.location
    except OperationalError:
        pass

    resp = client.get("/login/")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.data, 'html.parser')
    csrf_token = soup.find(id="csrf_token")["value"]
    resp = client.post(
        "/login/",
        data=dict(
            username="foo",
            password="bar",
            next="/",
            csrf_token=csrf_token
        ),
        follow_redirects=True
    )
    assert resp.status_code == 200
    yield client


class TestLoggedInBasicFlaskApp:

    @pytest.mark.parametrize("page", ["/account", "/history", "/dashboard"])
    def test_page_login(self, logged_in_client, page):
        """test that browsing to the account page while logged in goes on
        as intended"""
        resp = logged_in_client.get(page)
        assert resp.status_code == 200


class TestLoggedInFlaskRestxApp:
    def test_get_user(self, logged_in_client):
        resp = logged_in_client.get("/user/")
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.json

    def test_get_trading_sessions(self, logged_in_client):
        resp = logged_in_client.get("/trades_sessions/")
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.json is not None

    def test_post_trades_session(self, logged_in_client):
        resp = logged_in_client.post(
            "/trades_sessions/",
            data=json.dumps({
                "ticker": "foobar",
                "start_time": "2020-04-04T20:43:41.225Z",
            }),
            content_type='application/json'
        )
        assert resp.status_code == 201
        assert resp.is_json
        assert resp.json["session_id"]

        # TODO: cleanup

    def test_get_trades_session(self, logged_in_client):
        resp = logged_in_client.post(
            "/trades_sessions/",
            data=json.dumps({
                "ticker": "foobar",
                "start_time": "2020-04-04T20:43:41.225Z",
            }),
            content_type='application/json'
        )
        assert resp.status_code == 201
        assert resp.is_json
        session_id = resp.json["session_id"]
        resp = logged_in_client.get(
            f"/trades_sessions/{session_id}",
        )
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.json["session_id"] == session_id

    @pytest.mark.parametrize("url,is_paused,is_finished",
                             [
                                 ("/trades_sessions/{}/pause", True, False),
                                 ("/trades_sessions/{}/finish", False, True),
                                 ("/trades_sessions/{}/start", False, False)
                             ])
    def test_post_update_trade_session(self, logged_in_client, url, is_paused, is_finished):
        resp = logged_in_client.post(
            "/trades_sessions/",
            data=json.dumps({
                "ticker": "foobar",
                "start_time": "2020-04-04T20:43:41.225Z",
            }),
            content_type='application/json'
        )
        assert resp.status_code == 201
        assert resp.is_json
        session_id = resp.json["session_id"]
        resp = logged_in_client.post(url.format(session_id))
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.json["session_id"] == session_id
        assert resp.json["is_finished"] == is_finished
        assert resp.json["is_paused"] == is_paused

    def test_get_trades(self, logged_in_client):
        resp = logged_in_client.get("/trades/")
        assert resp.status_code == 200
        assert resp.is_json

    def test_post_trade(self, logged_in_client):
        resp = logged_in_client.post(
            "/trades_sessions/",
            data=json.dumps({
                "ticker": "foobar",
                "start_time": "2020-04-04T20:43:41.225Z",
            }),
            content_type='application/json'
        )
        assert resp.status_code == 201
        assert resp.is_json

        session_id = resp.json["session_id"]
        resp = logged_in_client.post(
            "/trades/",
            data=json.dumps({
                "session_id": session_id,
                "trade_type": "BUY",
                "price": 1,
                "volume": 1,
                "time_stamp": "2020-04-04T20:43:41.225Z",
            }),
            content_type='application/json'
        )
        assert resp.status_code == 201
        assert resp.is_json
        assert resp.json["trade_id"]

    def test_get_trade(self, logged_in_client):
        resp = logged_in_client.post(
            "/trades_sessions/",
            data=json.dumps({
                "ticker": "foobar",
                "start_time": "2020-04-04T20:43:41.225Z",
            }),
            content_type='application/json'
        )
        assert resp.status_code == 201
        assert resp.is_json

        session_id = resp.json["session_id"]
        resp = logged_in_client.post(
            "/trades/",
            data=json.dumps({
                "session_id": session_id,
                "trade_type": "BUY",
                "price": 1,
                "volume": 1,
                "time_stamp": "2020-04-04T20:43:41.225Z",
            }),
            content_type='application/json'
        )
        assert resp.status_code == 201
        assert resp.is_json
        trade_id = resp.json["trade_id"]
        resp = logged_in_client.get(
            f"/trades/{trade_id}",
        )
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.json["trade_id"] == trade_id


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


# TODO: using selenium to instrumentation test the dash "/dashboard" endpoint
# from dash.testing.application_runners import import_app
#
# @pytest.mark.xfail(reason="requires selenium install")
# def test_one(dash_duo):
#     app = import_app("autotradeweb.server.APP")
#     dash_duo.start_server(app)
#     dash_duo.wait_for_page(url="/dashboard", timeout=10)
