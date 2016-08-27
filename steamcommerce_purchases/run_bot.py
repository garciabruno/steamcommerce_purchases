#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from steamcommerce_api.core import models
import random

import os
import bot

if __name__ == '__main__':
    bot.log.info(u'Intializing PurchaseBot')

    halt_on_new_gid = True
    reset_gid = False

    purchasebot = bot.PurchaseBot()
    data = purchasebot.get_json_from_file('nin.json')

    if not os.path.isfile('session.pickle'):
        purchasebot.init_session(data)
    else:
        purchasebot.init_session_from_file('session.pickle')

        bot.log.info(u'Checking if session is still logged in')

        if not purchasebot.session_is_logged_in(data['account_name']):
            bot.log.info(u'Session got logged out! Re-logging in...')
            purchasebot.init_session(data)
        else:
            bot.log.info(u'Session is still logged in')

    count = 1

    req = purchasebot.session.get('http://store.steampowered.com')

    bot.log.debug(req.headers)
    bot.log.debug(req.cookies)

    f = open('debug/login.html', 'wb+')
    f.write(req.text.encode('utf-8'))
    f.close()

    products = [x for x in models.Product.select().where(
        models.Product.store_sub_id != None
    )]

    random_products = [random.choice(products) for x in xrange(20)]
    subids = [x.store_sub_id for x in random_products]

    if reset_gid:
        bot.log.info(u'Resetting shoppingCartGID')

        purchasebot.session.cookies.set('shoppingCartGID', None)

        purchasebot.session.cookies.set(
            'shoppingCartGID',
            None,
            domain='store.steampowered.com'
        )

    for subid in subids:
        bot.log.info(
            u'[{0}] Adding subid {1} to cart'.format(
                count, subid
            )
        )

        req = purchasebot.add_subid_to_cart(subid)

        f = open('debug/cart_%d.html' % count, 'wb+')
        f.write(req.text.encode('utf-8'))
        f.close()

        bot.log.debug(req.headers)
        bot.log.debug(req.cookies)

        received_new_gid = 'shoppingCartGID' in req.headers.get(
            'Set-Cookie',
            ''
        )

        if received_new_gid:
            bot.log.info(
                'Current shoppingCartGID is {0}'.format(
                    purchasebot.session.cookies.get('shoppingCartGID')
                )
            )

            purchasebot.save_session_to_file()

            if halt_on_new_gid:
                bot.log.info(u'Received a new gid, halting')

                break

        count += 1

    # purchasebot.cart_checkout(clear_shopping_cart=False)
