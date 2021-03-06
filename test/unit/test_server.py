#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""pytests for :mod:`.server`"""

import json
import os
from datetime import datetime

import pytest
from bs4 import BeautifulSoup

from autotradeweb.server import (
    APP,
    User,
    db,
    trading_session,
    trade,
    stock_prediction,
    stock_data,
)

# NOTE: to run these tests you must set a enviroment variable witht the database URI
# of autotradeweb postgresql test database
APP.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("TEST_DATABASE_URI")


def clear_user_related_db_entities():
    """delete all user related test database entities."""
    db.session.query(trade).delete()
    db.session.query(trading_session).delete()
    db.session.query(User).delete()
    db.session.commit()


def teardown_module(module):
    """delete all user related test database entities on test module exit"""
    clear_user_related_db_entities()


@pytest.fixture(scope="module")
def client():
    """init the autotradeweb flask app as a testing client"""
    flask_app = APP
    flask_app.config["DEBUG"] = True
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


class TestBasicFlaskApp:
    def test_static_files(self, client):
        resp = client.get("/static/stylesheet.css")
        assert resp.status_code == 200
        assert resp.content_type == "text/css; charset=utf-8"

    @pytest.mark.parametrize("page", ["/", "/api", "/register", "/login/"])
    def test_page_no_login_access(self, client, page):
        resp = client.get(page)
        assert resp.status_code == 200

    def test_logout(self, client):
        resp = client.get("/logout/")
        assert resp.status_code == 302

    @pytest.mark.parametrize(
        "page", ["/account", "/history", "/dashboard", "/statistics"]
    )
    def test_page_no_login_no_access(self, client, page):
        """test that browsing to the account page while logged out
        redirects the user to the login page"""
        resp = client.get(page)
        assert resp.status_code == 302
        assert "login" in resp.location

    def test_register_post(self, client):
        # TODO: does not work until we find way to emulate postgrelocally
        # setup empty the user table
        db.session.query(User).delete()
        db.session.commit()
        resp = client.post("/register", data={"email": "foo", "psw": "bar"})
        assert resp.status_code == 302
        assert "login" in resp.location

    def test_login_post(self, client):
        """register a user and attempt a login"""
        # setup empty the user table
        db.session.query(User).delete()
        db.session.commit()

        resp = client.post("/register", data={"email": "foo", "psw": "bar"})
        assert resp.status_code == 302
        assert "login" in resp.location

        resp = client.get("/login/")
        soup = BeautifulSoup(resp.data, "html.parser")
        csrf_token = soup.find(id="csrf_token")["value"]

        resp = client.post(
            "/login/",
            data=dict(username="foo", password="bar", next="/", csrf_token=csrf_token),
            follow_redirects=True,
        )
        assert resp.status_code == 200

        resp = client.get("/account")
        assert resp.status_code == 200
        resp = client.get("/logout/")
        assert resp.status_code == 302

    def test_login_post_invalid_user(self, client):
        """register a user and attempt a login"""
        # setup empty the user table
        db.session.query(User).delete()
        db.session.commit()

        resp = client.post("/register", data={"email": "foo", "psw": "bar"})
        assert resp.status_code == 302
        assert "login" in resp.location

        resp = client.get("/login/")
        soup = BeautifulSoup(resp.data, "html.parser")
        csrf_token = soup.find(id="csrf_token")["value"]

        resp = client.post(
            "/login/",
            data=dict(
                username="INVALID USERNAME",
                password="bar",
                next="/",
                csrf_token=csrf_token,
            ),
            follow_redirects=True,
        )
        assert resp.status_code == 401

    def test_login_post_invalid_password(self, client):
        """register a user and attempt a login"""
        # setup empty the user table
        db.session.query(User).delete()
        db.session.commit()

        resp = client.post("/register", data={"email": "foo", "psw": "bar"})
        assert resp.status_code == 302
        assert "login" in resp.location

        resp = client.get("/login/")
        soup = BeautifulSoup(resp.data, "html.parser")
        csrf_token = soup.find(id="csrf_token")["value"]

        resp = client.post(
            "/login/",
            data=dict(
                username="foo",
                password="INVALID PASSWORD",
                next="/",
                csrf_token=csrf_token,
            ),
            follow_redirects=True,
        )
        assert resp.status_code == 401


@pytest.fixture(scope="module")
def logged_in_client(client):
    """init the autotradeweb flask app as a testing client"""
    db.session.query(User).delete()
    db.session.commit()

    resp = client.post("/register", data={"email": "foo", "psw": "bar"})
    assert resp.status_code == 302
    assert "login" in resp.location

    resp = client.get("/login/")
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.data, "html.parser")
    csrf_token = soup.find(id="csrf_token")["value"]
    resp = client.post(
        "/login/",
        data=dict(username="foo", password="bar", next="/", csrf_token=csrf_token),
        follow_redirects=True,
    )
    assert resp.status_code == 200
    yield client


class TestLoggedInBasicFlaskApp:
    @pytest.mark.parametrize(
        "page", ["/account", "/history", "/dashboard", "/statistics"]
    )
    def test_page_login(self, logged_in_client, page):
        """test that browsing to the account page while logged in goes on
        as intended"""
        resp = logged_in_client.get(page)
        assert resp.status_code == 200


def create_trade_session(logged_in_client):
    """test helper to create a trade session via the API"""
    resp = logged_in_client.post(
        "/trades_sessions/",
        data=json.dumps({"ticker": "foobar", "start_time": "2020-04-04T20:43:41.225Z"}),
        content_type="application/json",
    )
    assert resp.status_code == 201
    assert resp.is_json
    return resp.json


def create_trade(logged_in_client):
    """test helper to create a trade via the API"""
    session = create_trade_session(logged_in_client)
    resp = logged_in_client.post(
        "/trades/",
        data=json.dumps(
            {
                "session_id": session["session_id"],
                "trade_type": "BUY",
                "price": 1,
                "volume": 1,
                "time_stamp": "2020-04-04T20:43:41.225Z",
            }
        ),
        content_type="application/json",
    )
    assert resp.status_code == 201
    assert resp.is_json
    return resp.json


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
            data=json.dumps(
                {"ticker": "foobar", "start_time": "2020-04-04T20:43:41.225Z"}
            ),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.is_json
        assert resp.json["session_id"]

    def test_get_trades_session(self, logged_in_client):
        session = create_trade_session(logged_in_client)
        resp = logged_in_client.get(f"/trades_sessions/{session['session_id']}")
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.json["session_id"] == session["session_id"]

    def test_get_trades_session_not_exist(self, logged_in_client):
        # setup delete all trade sessions
        db.session.query(trade).delete()
        db.session.query(trading_session).delete()
        db.session.commit()

        session = create_trade_session(logged_in_client)
        non_exist_session_id = session["session_id"] + 1

        resp = logged_in_client.get(f"/trades_sessions/{non_exist_session_id}")
        assert resp.status_code == 404

    @pytest.mark.parametrize(
        "url,is_paused,is_finished",
        [
            ("/trades_sessions/{}/pause", True, False),
            ("/trades_sessions/{}/finish", False, True),
            ("/trades_sessions/{}/start", False, False),
        ],
    )
    def test_post_update_trade_session(
        self, logged_in_client, url, is_paused, is_finished
    ):
        session = create_trade_session(logged_in_client)
        resp = logged_in_client.post(url.format(session["session_id"]))
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.json["session_id"] == session["session_id"]
        assert resp.json["is_finished"] == is_finished
        assert resp.json["is_paused"] == is_paused

    @pytest.mark.parametrize(
        "url,is_paused,is_finished",
        [
            ("/trades_sessions/{}/pause", True, False),
            ("/trades_sessions/{}/finish", False, True),
            ("/trades_sessions/{}/start", False, False),
        ],
    )
    def test_post_update_trade_session_not_exist(
        self, logged_in_client, url, is_paused, is_finished
    ):
        # setup delete all trade sessions
        db.session.query(trade).delete()
        db.session.query(trading_session).delete()
        db.session.commit()

        session = create_trade_session(logged_in_client)
        non_exist_session_id = session["session_id"] + 1
        resp = logged_in_client.post(url.format(non_exist_session_id))
        assert resp.status_code == 404

    def test_get_trades(self, logged_in_client):
        resp = logged_in_client.get("/trades/")
        assert resp.status_code == 200
        assert resp.is_json

    @pytest.mark.parametrize("trade_type", ["BUY", "SELL"])
    @pytest.mark.parametrize("price", [1, 1000])
    @pytest.mark.parametrize("volume", [1, 1000])
    def test_post_trade(self, logged_in_client, trade_type, price, volume):
        session = create_trade_session(logged_in_client)
        resp = logged_in_client.post(
            "/trades/",
            data=json.dumps(
                {
                    "session_id": session["session_id"],
                    "trade_type": trade_type,
                    "price": price,
                    "volume": volume,
                    "time_stamp": "2020-04-04T20:43:41.225Z",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 201
        assert resp.is_json
        assert resp.json["trade_id"]
        assert resp.json["trade_type"] == trade_type
        assert resp.json["price"] == price
        assert resp.json["volume"] == volume

    def test_post_trade_bad_trade_type(self, logged_in_client):
        session = create_trade_session(logged_in_client)
        resp = logged_in_client.post(
            "/trades/",
            data=json.dumps(
                {
                    "session_id": session["session_id"],
                    "trade_type": "INVALID TYPE",
                    "price": 1,
                    "volume": 1,
                    "time_stamp": "2020-04-04T20:43:41.225Z",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize("price", [0, -1, -1000, 0.0, -1.0, -1000.0])
    def test_post_trade_bad_price(self, logged_in_client, price):
        session = create_trade_session(logged_in_client)
        resp = logged_in_client.post(
            "/trades/",
            data=json.dumps(
                {
                    "session_id": session["session_id"],
                    "trade_type": "BUY",
                    "price": price,
                    "volume": 1,
                    "time_stamp": "2020-04-04T20:43:41.225Z",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize("volume", [0, -1, -1000, 0.0, -1.0, -1000.0])
    def test_post_trade_bad_volume(self, logged_in_client, volume):
        session = create_trade_session(logged_in_client)
        resp = logged_in_client.post(
            "/trades/",
            data=json.dumps(
                {
                    "session_id": session["session_id"],
                    "trade_type": "BUY",
                    "price": 1,
                    "volume": volume,
                    "time_stamp": "2020-04-04T20:43:41.225Z",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_post_trade_no_session(self, logged_in_client):
        # setup delete all trade sessions
        db.session.query(trade).delete()
        db.session.query(trading_session).delete()
        db.session.commit()

        resp = logged_in_client.post(
            "/trades/",
            data=json.dumps(
                {
                    "session_id": 0,  # since all trade sessions are deleted session_id point to nothing
                    "trade_type": "BUY",
                    "price": 1,
                    "volume": 1,
                    "time_stamp": "2020-04-04T20:43:41.225Z",
                }
            ),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_get_trade(self, logged_in_client):
        trade_ = create_trade(logged_in_client)
        trade_id = trade_["trade_id"]
        resp = logged_in_client.get(f"/trades/{trade_id}")
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.json["trade_id"] == trade_id

    def test_get_trade_no_session(self, logged_in_client):
        # setup delete all trade sessions
        db.session.query(trade).delete()
        db.session.query(trading_session).delete()
        db.session.commit()

        trade_id = 0
        resp = logged_in_client.get(f"/trades/{trade_id}")
        assert resp.status_code == 404

    def test_get_trade_not_exist(self, logged_in_client):
        # create a trade session and a trade
        trade_ = create_trade(logged_in_client)
        # setup delete all trade sessions
        db.session.query(trade).delete()
        db.session.commit()

        trade_id = trade_["trade_id"]
        resp = logged_in_client.get(f"/trades/{trade_id}")
        assert resp.status_code == 404


class TestDatabaseBindings:
    def test_add_user(self):
        db.session.query(User).delete()
        db.session.commit()
        user = User(username="foo", password="bar")
        db.session.add(user)
        db.session.commit()
        assert user.id is not None
        assert user.to_dict()

    def test_add_and_get_trading_session(self):
        # test add the trade session
        trading_session_add = trading_session(
            username="foo", ticker="bar", start_time=datetime.utcnow()
        )
        db.session.add(trading_session_add)
        db.session.commit()
        assert trading_session_add.session_id is not None
        assert trading_session_add.to_dict()

        # test get the trade session
        trading_session_get = (
            db.session.query(trading_session)
            .filter(trading_session.session_id == trading_session_add.session_id)
            .first()
        )
        assert trading_session_get
        assert trading_session_get.session_id is not None
        assert trading_session_get.to_dict()

    def test_add_and_get_trade(self):
        # add the required trading session
        trading_session_ = trading_session(
            username="foo", ticker="bar", start_time=datetime.utcnow()
        )
        db.session.add(trading_session_)
        db.session.commit()

        # test add the trade
        trade_add = trade(
            time_stamp=datetime.utcnow(),
            session_id=trading_session_.session_id,
            trade_type="BUY",
            volume=1,
            price=1,
        )
        db.session.add(trade_add)
        db.session.commit()
        assert trade_add.trade_id is not None

        # test get the trade
        trade_get = (
            db.session.query(trade).filter(trade.trade_id == trade_add.trade_id).first()
        )
        assert trade_get
        assert trade_get.trade_id is not None
        assert trade_get.to_dict()

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
