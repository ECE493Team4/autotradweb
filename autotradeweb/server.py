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
from flask_simplelogin import SimpleLogin, login_required

__log__ = getLogger(__name__)

from sqlalchemy import desc, func

APP = Flask(__name__)


DEFAULT_SQLITE_PATH = "sqlite:///autotradeweb.db"
APP.config['SQLALCHEMY_DATABASE_URI'] = DEFAULT_SQLITE_PATH
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(APP)


def validate_login(user):
    db_user = User.query.filter_by(username=user['username']).first()
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


SL_APP = SimpleLogin(APP, login_checker=validate_login)


class stock_data(db.Model):
    stock_name = db.Column(db.String(80), primary_key=True)
    time_stamp = db.Column(db.DateTime(), primary_key=True)
    open = db.Column(db.Float())
    high = db.Column(db.Float())
    low = db.Column(db.Float())
    close = db.Column(db.Float())
    volume = db.Column(db.Integer())


class User(db.Model):
    id = db.Column(db.Integer(), primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), index=True, unique=True, nullable=False)
    password = db.Column(db.String(80), index=True, unique=True, nullable=False)
    bank = db.Column(db.Float(), default=0.0, nullable=False)

    def __repr__(self):
        return '<User {}>'.format(self.username)


db.create_all()

##################
# main frontend
##################


@APP.route('/', methods=["GET"])
def index():
    return render_template('index.html')


@APP.route("/register", methods=["GET"])
def register():
    return render_template('register.html')


@APP.route("/register", methods=["POST"])
def register_submit():
    username = request.form.get('email')
    password = request.form.get('psw')

    new_user = User(username=username, password=password)

    db.session.add(new_user)
    db.session.commit()

    return redirect("/login")


@APP.route('/static/<path:path>')
def static_file(path):
    static_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static')
    return send_from_directory(static_folder, path)


##################
# dash frontend
##################


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

DASH = dash.Dash(__name__, server=APP, external_stylesheets=external_stylesheets)

DASH.layout = html.Div(
    style={
        "overflow-x": "hidden"
    },
    children=[
        html.Div(
            children=[
                html.H3(children=["Stock Value"]),
                dcc.Dropdown(
                    id='stock-dropdown',
                    options=[{}],
                    multi=False,
                    placeholder="Select a Stock...",
                ),
                html.H3(children=["Date Range"]),
                dcc.DatePickerRange(
                    id='date-picker-range',
                    end_date=datetime.utcnow(),
                    start_date=datetime.utcnow() - timedelta(days=30)
                ),
            ],
            style={
                "padding-left": "2em",
                "padding-right": "2em"
            }
        ),
        html.Div(
            children=[
                dcc.Graph(
                    id='stock-value-timeline-graph',
                    figure={
                        'data': [
                            {
                                'y': [],
                                'x': [],
                                'type': 'scatter',
                                'name': 'SF'
                            },
                        ],
                        'layout': {
                            'title': 'Stock Value',
                            'xaxis': {
                                'title': 'Datetime'
                            },
                            'yaxis': {
                                'title': 'Stock Value'
                            }
                        }
                    }
                ),
            ]
        )
    ]
)


@DASH.callback(Output('stock-dropdown', 'options'),
               [Input('stock-dropdown', 'value')])
@login_required
def set_stock_timeline_options(v):
    stocks = set(db.session.query(stock_data.stock_name))
    if stocks:
        return [{"label": str(stock.stock_name), "value": str(stock.stock_name)} for stock in stocks]
    return [{}]


@DASH.callback(Output('stock-value-timeline-graph', 'figure'),
               [
                    Input('date-picker-range', 'start_date'),
                    Input('date-picker-range', 'end_date'),
                    Input("stock-dropdown", 'value'),
                ])
@login_required
def update_stock_timeline(start_date, end_date, stock_id):
    stock_ticks = list(db.session.query(stock_data)
                       .filter(
                            stock_data.stock_name==stock_id,
                            func.date(stock_data.time_stamp) >= start_date,
                            func.date(stock_data.time_stamp) <= end_date,
                        )
                       .order_by(desc(stock_data.time_stamp))
                       .all())
    return {
        'data': [
            {
                'y': [str(m.open) for m in stock_ticks],
                'x': [m.time_stamp for m in stock_ticks],
                'type': 'scatter',
                'name': 'SF',
                'mode': 'markers'
            },
        ],
        'layout': {
            'title': 'Stock Value',
            'xaxis': {
                'title': 'Datetime'
            },
            'yaxis': {
                'title': 'Stock Value'
            }
        }
    }


DASH.config.suppress_callback_exceptions = True
DASH.css.config.serve_locally = True
DASH.scripts.config.serve_locally = True


@APP.route('/dashboard', methods=['GET', 'POST'])
@login_required
def stock_timeline():
    db.create_all()
    db.session.commit()
    return DASH.index()


@APP.route("/account")
@login_required
def account():
    return render_template("account.html")


@APP.route("/history")
@login_required
def history():
    return render_template("history.html")
