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
from flask import Flask, render_template, send_from_directory, request, redirect, \
    url_for, abort, Response
from flask_sqlalchemy import SQLAlchemy
from flask_simplelogin import SimpleLogin, login_required
from sqlalchemy import func

from autotradeweb.login_util import validate_login, create_user

__log__ = getLogger(__name__)

APP = Flask(__name__)
DEFAULT_SQLITE_PATH = "sqlite:///autotradeweb.db"
APP.config['SQLALCHEMY_DATABASE_URI'] = DEFAULT_SQLITE_PATH
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(APP)

SL_APP = SimpleLogin(APP, login_checker=validate_login)


class Stock(db.Model):
    id = db.Column(db.String(80), primary_key=True)
    symbol = db.Column(db.String(80))
    name = db.Column(db.String(80), nullable=False)
    value = db.Column(db.Float(), nullable=False)
    datetime = db.Column(db.DateTime)


class User(db.Model):
    username = db.Column(db.String(80), primary_key=True)
    password = db.Column(db.String(80), primary_key=True)
    bank = db.Column(db.Float(), default=0.0, nullable=False)
    trades = db.relationship('StockTrade', backref='user', lazy=True)


class StockTrade(db.Model):
    id = db.Column(db.String(80), primary_key=True)
    bought_stock = db.Column(db.String(80), db.ForeignKey('stock.id'), nullable=False)
    sold_stock = db.Column(db.String(80), db.ForeignKey('stock.id'), nullable=True)
    owner = db.Column(db.String(80), db.ForeignKey("user.username"), nullable=False)


db.create_all()

##################
# main frontend
##################


@APP.route('/', methods=["GET"])
def index():
    # parse request arguments
    return render_template('index.html')


@APP.route("/register", methods=["GET"])
def register():
    return render_template('register.html')


@APP.route("/register", methods=["POST"])
def register_submit():
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        # TODO: notify usercreation redirect to login
        return redirect("/login")
    except:
        return Response(
            "Username already taken.",
            status=400,
        )


@APP.route('/static/<path:path>')
def static_file(path):
    static_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static')
    return send_from_directory(static_folder, path)


##################
# dash frontend
##################


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

DASH = dash.Dash(__name__, server=APP, external_stylesheets=external_stylesheets)


slider_dates = {
    0: "Year",
    1: "Month",
    2: "Day",
    3: "Hour",
    4: "Minute",
    5: "Second"
}

date_bins = {
    0: "%Y",
    1: "%Y-%m",
    2: "%Y-%m-%d",
    3: "%Y-%m-%d-%H",
    4: "%Y-%m-%d-%H:%M",
    5: "%Y-%m-%d-%H:%M:%S"  # TODO: does not work very well should remove?
}


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
                    multi=True,
                    placeholder="Select a Stock...",
                ),
                html.H3(children=["Date Range"]),
                dcc.DatePickerRange(
                    id='date-picker-range',
                    end_date=datetime.utcnow(),
                    start_date=datetime.utcnow() - timedelta(days=1)
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
                html.Div(
                    children=[
                        html.H3(children=["Datetime Bin Size"]),
                        dcc.Slider(
                            id="date-binning-slider",
                            min=0,
                            max=5,
                            marks=slider_dates,
                            value=2,
                        ),
                    ],
                    style={
                        "margin-bottom": "2em",
                        "padding-left": "2em",
                        "padding-right": "2em"
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
    stocks = list(db.session.query(Stock.name, Stock.id))
    if stocks:
        return [{"label": "{} (id: {})".format(name, id), "value": id} for name, id in stocks]
    return [{}]



@DASH.callback(Output('stock-value-timeline-graph', 'figure'),
               [
                    Input('date-picker-range', 'start_date'),
                    Input('date-picker-range', 'end_date'),
                    Input("stock-dropdown", 'value'),
                    Input("date-binning-slider", "value")
                ])
@login_required
def update_stock_timeline(start_date, end_date, stock_id, bin):
    stock_ticks = list(db.session.query(func.count(Stock.id), Stock.datetime)
                    .filter(
                        func.date(Stock.datetime) >= start_date,
                        func.date(Stock.datetime) <= end_date,
                        Stock.id.in_(stock_id))
                    .group_by(func.strftime(date_bins[bin], Stock.datetime)))
    return {
        'data': [
            {
                'y': [str(m[0]) for m in stock_ticks],
                'x': [m[1] for m in stock_ticks],
                'type': 'scatter',
                'name': 'SF',
                'mode': 'lines+markers'
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
