#!/usr/bin/env python3

from flask import Flask


def loginPage():
    """
    This page should handle the login functionality
    """
    return "Hello World!"


def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()