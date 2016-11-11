#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import json
import datetime

from functools import partial


def datetime_to_str(obj):
    """Default JSON serializer."""

    if isinstance(obj, datetime.datetime):
        obj = str(obj)

    return obj


dumps = partial(json.dumps, default=datetime_to_str)
