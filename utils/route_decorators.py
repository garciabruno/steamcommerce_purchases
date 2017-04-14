#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import json

from functools import wraps


def as_json(f):
    @wraps(f)
    def as_json_inner(*args, **kwargs):
        response = f(*args, **kwargs)

        if type(response) == tuple and len(response) == 2:
            return (
                json.dumps(response[0]),
                response[1],
                {'Content-Type': 'application/json'}
            )

        return (
            json.dumps(response),
            200,
            {'Content-Type': 'application/json'}
        )

    return as_json_inner
