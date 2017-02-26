#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import config

from celery import Celery

app = Celery(
    'edge.tasks',
    backend=config.CELERY_RESULT_BACKEND,
    broker=config.CELERY_BROKER_URL
)
