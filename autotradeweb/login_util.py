#!/usr/bin/env python
# -*- coding: utf-8 -*-

""""""
import json

from flask import Flask, jsonify, render_template
from flask_simplelogin import SimpleLogin, login_required
from werkzeug.security import check_password_hash, generate_password_hash

def validate_login(user):
    # TODO: swap with database version
    db_users = json.load(open('users.json'))
    if not db_users.get(user['username']):
        return False
    stored_password = db_users[user['username']]['password']
    if check_password_hash(stored_password, user['password']):
        return True
    return False


def create_user(**data):
    """Creates user with encrypted password"""
    if 'username' not in data or 'password' not in data:
        raise ValueError('username and password are required.')

    # Hash the user password
    data['password'] = generate_password_hash(
        data.pop('password'),
        method='pbkdf2:sha256'
    )

    # Here you insert the `data` in your users database
    # for this simple example we are recording in a json file
    db_users = json.load(open('users.json'))
    # add the new created user to json
    db_users[data['username']] = data
    # commit changes to database
    json.dump(db_users, open('users.json', 'w'))
    return data
