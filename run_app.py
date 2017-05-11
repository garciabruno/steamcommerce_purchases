#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import config

from app import app

from core import steambot
from workers import WORKERS
from gevent.wsgi import WSGIServer

try:
    for network_id in WORKERS.keys():
        WORKERS[network_id].init()
except Exception, e:
    steambot.log.error(e)

    raise SystemExit

steambot.log.info('Starting HTTP Server on {0}:{1}'.format(config.HOST, config.PORT))

http_server = WSGIServer((config.HOST, config.PORT), app)

try:
    http_server.serve_forever()
except KeyboardInterrupt:
    steambot.log.info(u'Shutting down HTTP Server')

for network_id in WORKERS.keys():
    WORKERS[network_id].close()
