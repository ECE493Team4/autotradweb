#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Flask server definition"""

import os
from datetime import datetime, timedelta
from logging import getLogger

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from flask import Flask, render_template, send_from_directory, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_simplelogin import SimpleLogin, login_required, get_username
from flask_restx import Api, Resource, fields, abort
from sqlalchemy import desc, func

from sqlalchemy.dialects import postgresql


__log__ = getLogger(__name__)


APP = Flask(__name__)


DEFAULT_SQLITE_PATH = "sqlite:///autotradeweb.db"
APP.config["SQLALCHEMY_DATABASE_URI"] = DEFAULT_SQLITE_PATH
APP.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(APP)


##############
# Login page
# See SRS: S.9
##############

# See SRS: S.9.R.1
# See SRS: S.9.R.2
# See SRS: S.9.R.3
def validate_login(user):
    db_user = User.query.filter_by(username=user["username"]).first()
    if db_user is None:
        # no user of that username
        __log__.debug(f"login on nonexistant user: {user['username']}")
        return False
    if db_user.password == user["password"]:
        __log__.debug(f"logged in user: {user['username']}")
        return True
    else:
        # wrong password
        __log__.debug(f"invalid password for user: {user['username']}")
        return False


# See SRS: S.9.R.1
# See SRS: S.9.R.2
# See SRS: S.9.R.3
SL_APP = SimpleLogin(APP, login_checker=validate_login)


#################################
# Database Connection definitions
# See SRS: S.7.R.3
#################################


class trade(db.Model):
    trade_id = db.Column(
        db.Integer(), primary_key=True
    )  # autoincrement defined by server
    session_id = db.Column(db.Integer())
    trade_type = db.Column(db.String(80))
    price = db.Column(db.Float())
    volume = db.Column(db.Integer())
    time_stamp = db.Column(db.DateTime())

    def to_dict(self):
        return {
            "trade_id": int(self.trade_id),
            "session_id": int(self.session_id),
            "price": float(self.price),
            "volume": int(self.volume),
            "trade_type": str(self.trade_type),
            "time_stamp": self.time_stamp,
        }


class trading_session(db.Model):
    session_id = db.Column(
        db.Integer(), primary_key=True
    )  # autoincrement defined by server
    username = db.Column(db.String(80))
    ticker = db.Column(db.String(80))
    start_time = db.Column(db.DateTime())
    end_time = db.Column(db.DateTime())
    num_trades = db.Column(db.Integer, default=0)
    is_paused = db.Column(db.Boolean(), default=False)
    is_finished = db.Column(db.Boolean(), default=False)

    # TODO: is best way to serialize to dict?
    def to_dict(self):
        return {
            "session_id": int(self.session_id),
            "username": str(self.username),
            "ticker": str(self.ticker),
            "is_paused": self.is_paused,
            "is_finished": self.is_finished,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "num_trades": int(self.num_trades),
        }


class stock_data(db.Model):
    stock_name = db.Column(db.String(80), primary_key=True)
    time_stamp = db.Column(db.DateTime(), primary_key=True)
    open = db.Column(db.Float())
    high = db.Column(db.Float())
    low = db.Column(db.Float())
    close = db.Column(db.Float())
    volume = db.Column(db.Integer())


class stock_prediction(db.Model):
    stock_name = db.Column(db.String(80), primary_key=True)
    time_stamp = db.Column(db.DateTime(), primary_key=True)
    prediction = db.Column(postgresql.ARRAY(db.Float()))


class User(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), index=True, unique=True, nullable=False)
    password = db.Column(db.String(80), index=True, nullable=False)
    # TODO: NOTE: bank is set to 5000 for demo purposes
    bank = db.Column(db.Float(), default=5000.0, nullable=False)

    def to_dict(self):
        return {
            "id": int(self.id),
            "username": str(self.username),
            "bank": float(self.bank),
        }

    def __repr__(self):
        return "<User {}>".format(self.username)


def init_db():
    """helper function to intialize the database"""
    db.create_all()


###################
# main frontend
# See SRS: S.11.R.2
###################


@APP.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@APP.route("/static/<path:path>")
def static_file(path):
    static_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "static")
    return send_from_directory(static_folder, path)


##################
# register page
##################


@APP.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@APP.route("/register", methods=["POST"])
def register_submit():
    username = request.form.get("email")
    password = request.form.get("psw")

    new_user = User(username=username, password=password)

    db.session.add(new_user)
    db.session.commit()

    return redirect("/login")


###############
# Dashboard
# See SRS: S.10
###############


external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

DASH = dash.Dash(__name__, server=APP, external_stylesheets=external_stylesheets)

DASH.layout = html.Div(
    style={"overflow-x": "hidden"},
    children=[
        html.Div(
            children=[
                html.H3(children=["Stock Value"]),
                dcc.Dropdown(
                    id="stock-dropdown",
                    options=[{}],
                    multi=False,
                    placeholder="Select a Stock...",
                ),
                # See SRS: S.10.R.2
                # See SRS: S.10.R.6.D.1
                html.Button("Add trade session", id="add-trade-session"),
                html.Button("pause trade session", id="pause-trade-session"),
                html.Button("start trade session", id="start-trade-session"),
                html.Button("Finish trade session", id="finish-trade-session"),
                html.H3(children=["Date Range"]),
                dcc.DatePickerRange(
                    id="date-picker-range",
                    end_date=datetime.utcnow(),
                    start_date=datetime.utcnow() - timedelta(days=30),
                ),
            ],
            style={"padding-left": "2em", "padding-right": "2em"},
        ),
        html.Div(
            children=[
                dcc.Graph(
                    id="stock-value-timeline-graph",
                    figure={
                        "data": [{"y": [], "x": [], "type": "scatter", "name": "SF"}],
                        "layout": {
                            "title": "Stock Value",
                            "xaxis": {"title": "Datetime"},
                            "yaxis": {"title": "Stock Value"},
                        },
                    },
                )
            ]
        ),
    ],
)


# See SRS: S.10.R.6.D.1
@DASH.callback(
    Output("add-trade-session", "disabled"),
    [Input("add-trade-session", "n_clicks"), Input("stock-dropdown", "value")],
)
@login_required  # pylint: disable=function-redefined
def on_click(n_clicks, stock_id):
    username = get_username()
    trading_session_ = (
        db.session.query(trading_session)
        .filter(
            trading_session.is_finished != True,
            trading_session.ticker == stock_id,
            trading_session.username == username,
        )
        .first()
    )
    if trading_session_:  # only have one trading session for each stock ticker
        abort(409, f"trading session already exists for stock {stock_id}")
    else:
        __log__.debug(f"adding trading session for stock {stock_id}")
        new_trading_session_db = trading_session(
            username=username,
            start_time=datetime.now(),
            end_time=None,
            ticker=stock_id,
            is_paused=False,
            is_finished=False,
        )
        db.session.add(new_trading_session_db)
        db.session.commit()


@DASH.callback(
    Output("pause-trade-session", "disabled"),
    [Input("pause-trade-session", "n_clicks"), Input("stock-dropdown", "value")],
)
@login_required  # pylint: disable=function-redefined
def on_click(n_clicks, stock_id):
    __log__.debug(f"pausing trading session for stock {stock_id}")
    username = get_username()
    trading_session_ = (
        db.session.query(trading_session)
        .filter(
            trading_session.is_finished != True,
            trading_session.is_paused != True,
            trading_session.ticker == stock_id,
            trading_session.username == username,
        )
        .first()
    )
    if not trading_session_:
        abort(404, "running trading session not found")
    trading_session_.is_paused = True
    db.session.commit()


@DASH.callback(
    Output("start-trade-session", "disabled"),
    [Input("start-trade-session", "n_clicks"), Input("stock-dropdown", "value")],
)
@login_required  # pylint: disable=function-redefined
def on_click(n_clicks, stock_id):
    __log__.debug(f"starting trading session for stock {stock_id}")
    username = get_username()
    trading_session_ = (
        db.session.query(trading_session)
        .filter(
            trading_session.is_finished != True,
            trading_session.is_paused == True,
            trading_session.ticker == stock_id,
            trading_session.username == username,
        )
        .first()
    )
    if not trading_session_:
        abort(404, "paused trading session not found")
    trading_session_.is_paused = False
    db.session.commit()


@DASH.callback(
    Output("finish-trade-session", "disabled"),
    [Input("finish-trade-session", "n_clicks"), Input("stock-dropdown", "value")],
)
@login_required  # pylint: disable=function-redefined
def on_click(n_clicks, stock_id):
    __log__.debug(f"finishing trading session for stock {stock_id}")
    username = get_username()
    trading_session_ = (
        db.session.query(trading_session)
        .filter(
            trading_session.is_finished != True,
            trading_session.ticker == stock_id,
            trading_session.username == username,
        )
        .first()
    )
    if not trading_session_:
        abort(404, "trading session not found")
    trading_session_.is_finished = True
    db.session.commit()


@DASH.callback(Output("stock-dropdown", "options"), [Input("stock-dropdown", "value")])
@login_required
def set_stock_timeline_options(v):
    stocks = set(db.session.query(stock_data.stock_name))
    if stocks:
        return [
            {"label": str(stock.stock_name), "value": str(stock.stock_name)}
            for stock in stocks
        ]
    return [{}]


# See SRS: S.10.R.5
@DASH.callback(
    Output("stock-value-timeline-graph", "figure"),
    [
        Input("date-picker-range", "start_date"),
        Input("date-picker-range", "end_date"),
        Input("stock-dropdown", "value"),
    ],
)
@login_required
def update_stock_timeline(start_date, end_date, stock_id):
    stock_ticks = list(
        db.session.query(stock_data)
        .filter(
            stock_data.stock_name == stock_id,
            func.date(stock_data.time_stamp) >= start_date,
            func.date(stock_data.time_stamp) <= end_date,
        )
        .order_by(desc(stock_data.time_stamp))
        .all()
    )

    try:
        end_datetime = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S.%f")
    except:
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d")

    prediction_end_date = (end_datetime + timedelta(days=2)).strftime(
        "%Y-%m-%dT%H:%M:%S.%f"
    )
    stock_predictions = list(
        db.session.query(stock_prediction)
        .filter(
            stock_prediction.stock_name == stock_id,
            func.date(stock_prediction.time_stamp) >= start_date,
            func.date(stock_prediction.time_stamp) <= prediction_end_date,
        )
        .order_by(desc(stock_prediction.time_stamp))
        .all()
    )

    # TODO: cleanup
    predictors = []
    for stock_prediction_ in stock_predictions:
        x = []
        y = []
        for hour, p in enumerate(stock_prediction_.prediction):
            x.append(stock_prediction_.time_stamp + timedelta(hours=hour))
            y.append(p)
        # TODO: makes ugly rainbow garbage need to concentrate down
        predictors.append(
            {
                "y": y,
                "x": x,
                "type": "scatter",
                "name": f"prediction from {stock_prediction_.time_stamp}",
                "mode": "lines",
            }
        )

    return {
        "data": [
            {
                "y": [str(m.open) for m in stock_ticks],
                "x": [m.time_stamp for m in stock_ticks],
                "type": "scatter",
                "name": "actual values",
                "mode": "markers",
            }
        ]
        + predictors,
        "layout": {
            "title": "Stock Value",
            "xaxis": {"title": "Datetime"},
            "yaxis": {"title": "Stock Value"},
        },
    }


DASH.config.suppress_callback_exceptions = True
DASH.css.config.serve_locally = True
DASH.scripts.config.serve_locally = True


@APP.route("/dashboard", methods=["GET", "POST"])
@login_required
def stock_timeline():
    db.create_all()
    db.session.commit()
    return DASH.index()


####################
# History Page
# See SRS: S.12
####################


@APP.route("/history")
@login_required
def history():
    return render_template("history.html")


@APP.route("/statistics")
@login_required
def statistics():
    return render_template("statistics.html")


####################
# Account Page
# See SRS: S.13
####################


@APP.route("/account")
@login_required
def account():
    return render_template("account.html")


######################
# API
# See SRS: S.7.R.3.D.1
######################

api = Api(
    APP,
    version="0.0.0",
    title="AutoTrade API",
    doc="/api",
    description="Official API for AutoTrade",
)

trading_sessions_ns = api.namespace(
    "trades_sessions", description="trading session operations"
)

TRADING_SESSION = api.model(
    "trading_sessions",
    {
        "session_id": fields.Integer(
            required=False, description="id of the trading session"
        ),
        "ticker": fields.String(required=True, description="name of the stock"),
        "is_paused": fields.Boolean(default=False),
        "is_finished": fields.Boolean(default=False),
        "start_time": fields.DateTime(),
        "end_time": fields.DateTime(),
        "num_trades": fields.Integer(default=0),
    },
)


@trading_sessions_ns.route("/")
class TradingSessionList(Resource):
    @login_required(basic=True)
    @trading_sessions_ns.doc("list all stock orders")
    @trading_sessions_ns.marshal_list_with(TRADING_SESSION)
    def get(self):
        """Get the list of all trade sessions for the currently logged in user"""
        username = get_username()
        trading_sessions = (
            db.session.query(trading_session)
            .filter(trading_session.username == username)
            .all()
        )
        return [trading_session_.to_dict() for trading_session_ in trading_sessions]

    # TODO: using basic here makes unit test fails (maybe this is a issue with flask-restx?)
    @login_required()
    @trading_sessions_ns.expect(TRADING_SESSION)
    @trading_sessions_ns.marshal_with(TRADING_SESSION, code=201)
    def post(self):
        """Add a trade session to the currently logged in user"""
        new_trading_session = api.payload

        # TODO: ensure ticker is valid
        username = get_username()
        new_trading_session_db = trading_session(
            username=username,
            start_time=new_trading_session["start_time"],
            end_time=new_trading_session.get("end_time"),
            ticker=new_trading_session["ticker"],
            is_paused=new_trading_session.get("is_paused", False),
            is_finished=new_trading_session.get("is_finished", False),
        )
        db.session.add(new_trading_session_db)
        db.session.commit()
        return new_trading_session_db.to_dict(), 201


@trading_sessions_ns.route("/<int:session_id>")
@trading_sessions_ns.response(404, "trading session not found")
class TradingSession(Resource):
    @login_required(basic=True)
    @trading_sessions_ns.doc("get_todo")
    @trading_sessions_ns.marshal_with(TRADING_SESSION)
    def get(self, session_id):
        """Get a trade session for the currently logged in user""" ""
        username = get_username()
        trading_session_ = (
            db.session.query(trading_session)
            .filter(
                trading_session.session_id == session_id,
                trading_session.username == username,
            )
            .first()
        )
        if not trading_session_:
            abort(404, "trading session not found")
        return trading_session_.to_dict()


@trading_sessions_ns.route("/<int:session_id>/pause")
class TradingSessionPause(Resource):
    @login_required(basic=True)
    @trading_sessions_ns.marshal_with(TRADING_SESSION)
    def post(self, session_id):
        """Pause a trading session"""
        username = get_username()
        trading_session_ = (
            db.session.query(trading_session)
            .filter(
                trading_session.session_id == session_id,
                trading_session.username == username,
            )
            .first()
        )
        if not trading_session_:
            abort(404, "trading session not found")
        trading_session_.is_paused = True
        db.session.commit()
        return trading_session_.to_dict()


@trading_sessions_ns.route("/<int:session_id>/start")
class TradingSessionStart(Resource):
    @login_required(basic=True)
    @trading_sessions_ns.marshal_with(TRADING_SESSION)
    def post(self, session_id):
        """Restart/unpause a trading session"""
        username = get_username()
        trading_session_ = (
            db.session.query(trading_session)
            .filter(
                trading_session.session_id == session_id,
                trading_session.username == username,
            )
            .first()
        )
        if not trading_session_:
            abort(404, "trading session not found")
        trading_session_.is_paused = False
        db.session.commit()
        return trading_session_.to_dict()


@trading_sessions_ns.route("/<int:session_id>/finish")
class TradingSessionFinish(Resource):
    @login_required(basic=True)
    @trading_sessions_ns.marshal_with(TRADING_SESSION)
    def post(self, session_id):
        """Finish a trading session

        .. warning::
            This action is irreversible
        """
        username = get_username()
        trading_session_ = (
            db.session.query(trading_session)
            .filter(
                trading_session.session_id == session_id,
                trading_session.username == username,
            )
            .first()
        )
        if not trading_session_:
            abort(404, "trading session not found")
        trading_session_.is_finished = True
        db.session.commit()
        return trading_session_.to_dict()


trade_ns = api.namespace("trades", description="stock trade operations")

TRADE = api.model(
    "trade",
    {
        "trade_id": fields.Integer(
            required=False, description="id of of the stock trade"
        ),
        "session_id": fields.Integer(
            required=True, description="id of the related stock trading session"
        ),
        "trade_type": fields.String(
            required=True, description="type of trade (BUY|SELL)"
        ),
        "price": fields.Float(required=True, description="name of the stock"),
        "volume": fields.Integer(required=True),
        "time_stamp": fields.DateTime(),
    },
)


@trade_ns.route("/")
class TradeList(Resource):
    @login_required(basic=True)
    @trade_ns.marshal_list_with(TRADE)
    def get(self):
        """Get the list of all stock trades for the currently logged in user"""
        username = get_username()
        trading_sessions_ids = (
            db.session.query(trading_session.session_id)
            .filter(trading_session.username == username)
            .all()
        )
        trades = (
            db.session.query(trade)
            .filter(trade.session_id.in_(trading_sessions_ids))
            .all()
        )
        return [trade_.to_dict() for trade_ in trades]

    # TODO: using basic here makes unit test fails (maybe this is a issue with flask-restx?)
    @login_required()
    @trade_ns.expect(TRADE)
    @trade_ns.marshal_with(TRADE, code=201)
    def post(self):
        """Add a stock trade to the currently logged in user"""
        new_trade = api.payload

        # trade type is BUY or SELL
        if new_trade["trade_type"] not in ["BUY", "SELL"]:
            abort(400, "trade_type must be either BUY or SELL")

        # ensure volume>1
        if new_trade["volume"] < 1:
            abort(400, "volume must be a integer equal to or greater than 1")

        # ensure price>0
        if new_trade["price"] <= 0:
            abort(400, "price must be greater than 0")

        # get the session id by the currently non_paused trading session
        username = get_username()
        trading_session_id = (
            db.session.query(trading_session.session_id)
            .filter(
                trading_session.username == username,
                trading_session.session_id == new_trade["session_id"],
                trading_session.is_finished == False,
                trading_session.is_paused == False,
            )
            .first()
        )
        if trading_session_id is None:
            abort(404, "trading session not found")

        new_trade_db = trade(
            price=new_trade["price"],
            trade_type=new_trade["trade_type"],
            volume=new_trade["volume"],
            session_id=new_trade["session_id"],
            time_stamp=new_trade["time_stamp"],
        )
        db.session.add(new_trade_db)
        db.session.commit()
        return new_trade_db.to_dict(), 201


@trade_ns.route("/<int:trade_id>")
class Trade(Resource):
    # TODO: using basic here makes unit test fails (maybe this is a issue with flask-restx?)
    @login_required()
    @trade_ns.marshal_with(TRADE)
    def get(self, trade_id):
        """Get a stock trade for the currently logged in user"""
        username = get_username()
        trading_sessions_ids = (
            db.session.query(trading_session.session_id)
            .filter(trading_session.username == username)
            .all()
        )
        if not trading_sessions_ids:
            abort(404, "no trading sessions for user")
        trade_ = (
            db.session.query(trade)
            .filter(
                trade.trade_id == trade_id, trade.session_id.in_(trading_sessions_ids)
            )
            .first()
        )
        if not trade_:
            abort(404, "trade not found")
        return trade_.to_dict()


user_ns = api.namespace("user", description="user operations")
USER = api.model(
    "user",
    {
        "bank": fields.Float(
            required=True, default=0.0, description="The user's liquid cash assets"
        ),
        "username": fields.String(required=True, description="Name of the user"),
    },
)


@user_ns.route("/")
class APIUser(Resource):
    @login_required(basic=True)
    @user_ns.marshal_list_with(USER)
    def get(self):
        """Get the currently logged in user"""
        username = get_username()
        user_ = db.session.query(User).filter(User.username == username).first()
        return user_.to_dict()
