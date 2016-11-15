#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import json
import requests

import enums
import config
import commander

from steamcommerce_api.api import logger

log = logger.Logger('SteamCommerce Commander', 'commander.log').get_logger()

BOTS = config.BOTS
ACCOUNT_IDS = config.ACCOUNT_IDS

log.info(u'Starting Commander Cron')

relations = commander.Commander().get_pending_relations()

for currency in relations.keys():
    if not currency in config.BOTS.keys():
        log.info(
            u'Got relations for currency {} but not bot was found'.format(
                currency
            )
        )

        continue

    if not len(relations[currency]):
        log.info(u'List of items for {0} is empty'.format(currency))

        continue

    try:
        req = requests.post(
            BOTS[currency] + '/bot/cart/add/',
            data={'items': json.dumps(relations[currency])},
            timeout=120
        )
    except Exception, e:
        log.error(
            u'Could not contact {0} ({1}): {2}'.format(
                BOTS[currency],
                currency,
                e
            )
        )

        continue

    if req.status_code != 200:
        log.error(
            u'Received status code {0} from {1} ({2})'.format(
                req.status_code,
                BOTS[currency],
                currency
            )
        )

        continue

    log.info(u'Pushing items to {0} ({1})'.format(BOTS[currency], currency))

    try:
        response = req.json()
    except Exception, e:
        log.error(
            u'Could not serialize response from {0}: {1}'.format(
                BOTS[currency],
                e
            )
        )

    try:
        reply = enums.EBotResult(response.get('result'))
    except ValueError:
        reply = enums.ECartResult(response.get('result'))

    log.info(
        u'Received {0} as reply from {1} ({2})'.format(
            reply.__repr__(),
            BOTS[currency],
            currency
        )
    )

    result = response.get('result')

    if (
        result == enums.EBotResult.Succeded or
        result == enums.EBotResult.ReachedMaxCartCount or
        result == enums.EBotResult.ReachedMaxCartTimespan
    ):
        log.info(
            u'Processing results from {0} ({1})'.format(
                BOTS[currency],
                currency
            )
        )

        commander.Commander().process_bot_results(response)

    if (
        result == enums.EBotResult.ReachedMaxCartCount or
        result == enums.EBotResult.ReachedMaxCartTimespan
    ):
        log.info(
            u'Received {0}, calling bot to checkout cart'.format(
                enums.EBotResult(result).__repr__()
            )
        )

        log.info(
            u'Calling checkout on {0} ({1})'.format(
                BOTS[currency],
                currency
            )
        )

        req = requests.post(
            BOTS[currency] + '/bot/cart/checkout/',
            data={
                'bot_id': response.get('id'),
                'country_code': currency,
                'giftee_account_id': ACCOUNT_IDS[currency]
            },
            timeout=120
        )

        if req.status_code != 200:
            log.error(
                u'Received status code {0} from {1} ({2})'.format(
                    req.status_code,
                    BOTS[currency],
                    currency
                )
            )

            continue

        reply = enums.EPurchaseResult(int(req.text))

        log.info(
            u'Received {0} from {1} ({2})'.format(
                reply.__repr__(),
                BOTS[currency],
                currency
            )
        )
