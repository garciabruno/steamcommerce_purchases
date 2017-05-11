#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import config
from core import steambot

WORKERS = {}

for network_id in config.ENABLED_ACCOUNTS:
    data = steambot.get_data_from_file('data/{}.json'.format(network_id))

    WORKERS[str(network_id)] = steambot.SteamBot(
        account_name=data.get('account_name'),
        password=data.get('password'),
        shared_secret=data.get('shared_secret')
    )
