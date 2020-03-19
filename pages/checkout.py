#!/usr/bin/env python3

from flask import Flask

def checkout():
    """
    This page will try to lock a car to a user.
    It should return an error if the car is in use.
    Otherwise it should provide a method to generate one time passwords.
    """
    return '{"Error":"Failure"}'