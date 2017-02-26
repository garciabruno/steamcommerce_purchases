#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from flask import Flask

import config

app = Flask(__name__)
app.config.from_object(config)

from blueprints.edge import edge

BLUEPRINTS = [edge]

for blueprint in BLUEPRINTS:
    app.register_blueprint(
        blueprint,
        url_prefix=config.BLUEPRINT_ENDPOINTS[blueprint.name]
    )
