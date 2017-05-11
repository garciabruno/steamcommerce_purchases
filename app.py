#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from flask import Flask
from flask import got_request_exception

import os
import rollbar
import rollbar.contrib.flask

import config

app = Flask(__name__)
app.config.from_object(config)

from blueprints.edge import edge
from blueprints.isteamuser import isteamuser

BLUEPRINTS = [edge, isteamuser]

for blueprint in BLUEPRINTS:
    app.register_blueprint(
        blueprint,
        url_prefix=config.BLUEPRINT_ENDPOINTS[blueprint.name]
    )


@app.before_first_request
def init_rollbar():
    """init rollbar module"""

    rollbar.init(
        config.ROLLBAR_TOKEN,
        'env',
        root=os.path.dirname(os.path.realpath(__file__)),
        allow_logging_basic_config=False
    )

    # send exceptions from `app` to rollbar, using flask's signal system.

    got_request_exception.connect(
        rollbar.contrib.flask.report_exception,
        app
    )
