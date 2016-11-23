#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import json
import datetime
import requests

import enums
import config
import commander

from steamcommerce_api.api import logger

log = logger.Logger('SteamCommerce Commander', 'commander.log').get_logger()

BOTS = config.BOTS
ACCOUNT_IDS = config.ACCOUNT_IDS


class Cron(object):
    def push_relations(self):
        relations = commander.Commander().get_pending_relations()

        for currency in relations.keys():
            if not currency in config.BOTS.keys():
                log.info(
                    u'Got relations for currency {} but not bot was'
                    ' found'.format(
                        currency
                    )
                )

                continue

            if not len(relations[currency]):
                log.info(u'List of items for {0} is empty'.format(currency))

                continue

            log.info(
                u'Pushing {0} items to {1} ({2})'.format(
                    len(relations[currency]),
                    BOTS[currency],
                    currency
                )
            )

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

            try:
                response = req.json()
            except Exception, e:
                log.error(
                    u'Could not serialize response from {0}: {1}'.format(
                        BOTS[currency],
                        e
                    )
                )

                continue

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

                self.call_bot_checkout(currency, response.get('id'))

    def call_bot_checkout(self, currency, bot_id):
        log.info(
            u'Calling checkout on {0} ({1})'.format(
                BOTS[currency],
                currency
            )
        )

        req = requests.post(
            BOTS[currency] + '/bot/cart/checkout/',
            data={
                'bot_id': bot_id,
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

            return None

        purchase_response = json.loads(req.text)

        try:
            reply = enums.EBotResult(purchase_response[0])
        except ValueError:
            reply = enums.EPurchaseResult(purchase_response[0])

        log.info(
            u'Received {0} from {1} ({2})'.format(
                reply.__repr__(),
                BOTS[currency],
                currency
            )
        )

        if reply == enums.EPurchaseResult.Succeded:
            log.info(
                u'Commiting all relations with shopping'
                ' cart gid {0} on bot {1}'.format(
                    purchase_response[1],
                    purchase_response[2]
                )
            )

            commander.Commander().commit_purchased_relations(
                purchase_response[1],
                purchase_response[2]
            )

    def check_all_bots(self):
        for currency in BOTS.keys():
            log.info(
                u'Checking status of all bots in {0} ({1})'.format(
                    currency,
                    BOTS[currency]
                )
            )

            try:
                req = requests.get(
                    BOTS[currency] + '/bots/report/',
                    params={'json': 1}
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

            try:
                response = req.json()
            except Exception, e:
                log.error(
                    u'Could not serialize response from {0}: {1}'.format(
                        BOTS[currency],
                        e
                    )
                )

                continue

            for bot_data in response:
                last_cart_push = datetime.datetime.strptime(
                    bot_data['last_cart_push'],
                    '%Y-%m-%d %H:%M:%S.%f'
                )

                time_diff = (datetime.datetime.utcnow() - last_cart_push)
                timespan = bot_data.get('max_timespan_until_purchase')

                current_cart_count = bot_data.get('current_cart_count')
                max_cart_count = bot_data.get('max_cart_until_purchase')

                reached_max_timespan = time_diff.total_seconds() > timespan
                reached_max_cart_count = current_cart_count > max_cart_count

                if (reached_max_timespan or reached_max_cart_count):
                    if (current_cart_count > 0):
                        log.info(
                            u'Reached {}, calling bot to checkout cart'.format(
                                'Max timespan' if reached_max_timespan else
                                'Max cart count'
                            )
                        )

                        self.call_bot_checkout(currency, bot_data.get('id'))

if __name__ == '__main__':
    log.info(u'Starting Commander Cron')

    cron = Cron()

    cron.push_relations()
    cron.check_all_bots()
