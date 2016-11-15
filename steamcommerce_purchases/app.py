#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import os
import re
import json
import datetime

from flask import Flask
from flask import request

from functools import wraps

import bot
import enums
import items as crawler_items
import config
import json_util
import controller


app = Flask(__name__)
app.config.from_object(config)
app.secret_key = config.SECRET_KEY

CHECKOUT_LINK = 'https://store.steampowered.com/checkout/?purchasetype=gift'


def as_json(f):
    @wraps(f)
    def as_json_inner(*args, **kwargs):
        response = f(*args, **kwargs)

        if type(response) == tuple and len(response) == 2:
            return (
                json_util.dumps(response[0]),
                response[1],
                {'Content-Type': 'application/json'}
            )

        return (
            json_util.dumps(response),
            200,
            {'Content-Type': 'application/json'}
        )

    return as_json_inner


@app.route('/bots/report/')
@as_json
def bots_report():
    bots = controller.BotController().get_bots()

    return [x._data for x in bots]


@app.route('/bots/sync/')
@as_json
def bots_sync():
    bots = controller.BotController().get_bots()

    for bot_obj in bots:
        purchasebot = bot.PurchaseBot(
            data_path=os.path.join(
                os.getcwd(),
                'data',
                bot_obj.data_filename
            ),
            pickle_path=os.path.join(
                os.getcwd(),
                'data',
                bot_obj.session_filename
            )
        )

        purchasebot.init_bot()
        purchasebot.sync_data(bot_obj.id)

    return {'success': True}


@app.route('/bot/cart/add/', methods=['POST'])
@as_json
def cart_add():
    '''
    Push items to cart in the form of
    [
        {
            'subid': subid,
            'relation_id': relation_id,
            'relation_type': relation_type
        },
        ...
    ]
    '''

    response = {}

    items = json.loads(request.form.get('items', '[]'))
    bot_obj = controller.BotController().get_first_active_bot()

    if bot_obj == enums.EBotResult.NotBotAvailableFound:
        response.update({
            'result': enums.EBotResult.NotBotAvailableFound
        })

        return response
    elif bot_obj == enums.EBotResult.RaisedUnknownException:
        response.update({
            'result': enums.EBotResult.RaisedUnknownException
        })

        return response

    purchasebot = bot.get_purchasebot(bot_obj)
    response.update({'id': bot_obj.id})

    if purchasebot == enums.EBotResult.NotBotAvailableFound:
        response.update({
            'result': enums.EBotResult.NotBotAvailableFound
        })

        return response

    results = []

    controller.BotController().set_bot_state(
        bot_obj.id,
        enums.EBotState.PushingItemsToCart.value
    )

    current_cart_count = bot_obj.current_cart_count

    if current_cart_count >= bot_obj.max_cart_until_purchase:
        controller.BotController().set_bot_state(
            bot_obj.id,
            enums.EBotState.StandingBy.value
        )

        response.update({
            'items': results,
            'result': enums.EBotResult.ReachedMaxCartCount
        })

        return response

    for item in items:
        last_shopping_cart_gid = purchasebot.get_shopping_cart_gid()

        req = purchasebot.add_subid_to_cart(item['subid'])
        item_added = 'YOUR ITEM\'S BEEN ADDED!' in req.text

        if (
            purchasebot.get_shopping_cart_gid() != last_shopping_cart_gid
            and last_shopping_cart_gid is not None
        ):
            bot.log.info(
                u'Got a new shoppingCartGid: {0}'.format(
                    purchasebot.get_shopping_cart_gid()
                )
            )

            bot.log.info(
                u'shoppingCartGid {0} appears to have been reset'.format(
                    last_shopping_cart_gid
                )
            )

            bot.log.info(
                u'Removing all items with shoppingCartGid {0}'.format(
                    last_shopping_cart_gid
                )
            )

            results = filter(
                lambda x: x['shoppingCartGid'] != last_shopping_cart_gid,
                results
            )

            if not 'failed_gids' in response.keys():
                response['failed_gids'] = []

            response['failed_gids'].append(last_shopping_cart_gid)

        if (
            purchasebot.get_shopping_cart_gid() != last_shopping_cart_gid
            and last_shopping_cart_gid is not None
        ):
            bot.log.info(
                u'shoppingCartGid {0} appears to have been reset'.format(
                    last_shopping_cart_gid
                )
            )

            bot.log.info(
                u'Removing all items with shoppingCartGid {0}'.format(
                    last_shopping_cart_gid
                )
            )

            results = filter(
                lambda x: x['shoppingCartGid'] != last_shopping_cart_gid,
                results
            )

            if not 'failed_gids' in response.keys():
                response['failed_gids'] = []

            response['failed_gids'].append(last_shopping_cart_gid)
        elif item_added:
            if not CHECKOUT_LINK in req.text:
                bot.log.info(
                    u'Subid {0} caused cart not to be gifteable'.format(
                        item.get('subid')
                    )
                )

                carts = crawler_items.SteamCart.all_from(req.text)

                if not len(carts):
                    response.update({
                        'items': results,
                        'result':
                        enums.ECartResult.UnableToRetrieveCartFromCrawler
                    })

                    controller.BotController().set_bot_state(
                        bot_obj.id,
                        enums.EBotState.StandingBy.value
                    )

                    return response

                try:
                    cart_item_gid_matches = re.findall(
                        r'([0-9]+)',
                        carts[0].items[0].remove_button,
                        re.DOTALL
                    )
                except IndexError:
                    bot.log.error(
                        u'IndexError on cart gid matches: {0}'.format(
                            purchasebot.get_shopping_cart_gid()
                        )
                    )

                    continue

                if not len(cart_item_gid_matches):
                    response.update({
                        'items': results,
                        'result': enums.ECartResult.UnableToRetrieveCartItemGid
                    })

                    controller.BotController().set_bot_state(
                        bot_obj.id,
                        enums.EBotState.StandingBy.value
                    )

                    return response

                cartitem_gid = cart_item_gid_matches[0]

                purchasebot.remove_gid_from_cart(cartitem_gid)

                continue

            purchasebot.sync_data(bot_obj.id, req=req)
            controller.BotController().set_last_cart_push(bot_obj.id)

            result = dict(item)
            result['shoppingCartGid'] = purchasebot.get_shopping_cart_gid()

            results.append(result)

            if (current_cart_count + 1) >= bot_obj.max_cart_until_purchase:
                response.update({
                    'items': results,
                    'result': enums.EBotResult.ReachedMaxCartCount
                })

                controller.BotController().set_bot_state(
                    bot_obj.id,
                    enums.EBotState.StandingBy.value
                )

                return response

    # This is intentionally old data

    minutes_since_last_push = (
        datetime.datetime.now() -
        (bot_obj.last_cart_push or datetime.datetime.now())
    ).total_seconds() / 60

    if minutes_since_last_push >= bot_obj.max_timespan_until_purchase:
        response.update({
            'items': results,
            'result': enums.EBotResult.ReachedMaxCartTimespan
        })

        controller.BotController().set_bot_state(
            bot_obj.id,
            enums.EBotState.StandingBy.value
        )

        return response

    response.update({
        'items': results,
        'result': enums.EBotResult.Succeded
    })

    controller.BotController().set_bot_state(
        bot_obj.id,
        enums.EBotState.StandingBy.value
    )

    return response


@app.route('/bot/cart/info/<int:bot_id>')
@as_json
def bot_cart_info(bot_id):
    if not bot_id:
        return enums.EBotResult.NotBotAvailableFound

    bot_obj = controller.BotController().get_bot_id(bot_id)

    if not isinstance(bot_obj, controller.BotController().model):
        return bot_obj

    purchasebot = bot.get_purchasebot(bot_obj)

    if not isinstance(purchasebot, bot.PurchaseBot):
        return purchasebot

    req = purchasebot.session.get('https://store.steampowered.com/cart')
    items = crawler_items.SteamCart.all_from(req.text)

    if not len(items):
        return enums.ECartResult.UnableToRetrieveCartFromCrawler

    cart = items[0]

    response = {
        'count': cart.count,
        'subtotal': cart.subtotal,
        'balance': cart.balance,
        'items': []
    }

    for cart_item in cart.items:
        response['items'].append({
            'appid': cart_item.appid,
            'packageid': cart_item.packageid,
            'title': cart_item.title,
            'price': cart_item.price,
            'remove_button': cart_item.remove_button
        })

    purchasebot.sync_data(bot_obj.id, req=req)

    return response


@app.route('/bot/cart/checkout/', methods=['POST'])
@as_json
def bot_cart_checkout():
    bot_id = request.form.get('bot_id')
    country_code = request.form.get('country_code')
    giftee_account_id = request.form.get('giftee_account_id')

    if not bot_id:
        return enums.EBotResult.NotBotAvailableFound

    if not giftee_account_id or not country_code:
        return enums.EBotResult.RaisedUnknownException

    bot_obj = controller.BotController().get_bot_id(int(bot_id))

    if not isinstance(bot_obj, controller.BotController().model):
        return bot_obj

    purchasebot = bot.get_purchasebot(bot_obj)

    if not isinstance(purchasebot, bot.PurchaseBot):
        return purchasebot

    controller.BotController().set_bot_state(
        bot_obj.id,
        enums.EBotState.PurchasingCart.value
    )

    purchase_result = purchasebot.cart_checkout(
        giftee_account_id,
        country_code
    )

    if purchase_result == enums.EPurchaseResult.InsufficientFunds:
        controller.BotController().set_bot_state(
            bot_obj.id,
            enums.EBotState.WaitingForSufficientFunds.value
        )
    elif purchase_result == enums.EPurchaseResult.Succeded:
        purchasebot.sync_data(bot_obj.id)

        controller.BotController().set_last_cart_purchase(bot_obj.id)

        controller.BotController().set_bot_state(
            bot_obj.id,
            enums.EBotState.StandingBy.value
        )
    else:
        controller.BotController().set_bot_state(
            bot_obj.id,
            enums.EBotState.BlockedForUnknownReason.value
        )

    return purchase_result
