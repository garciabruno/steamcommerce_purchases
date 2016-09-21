#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from steamcommerce_api.core import models
import random

import os
import bot

if __name__ == '__main__':
    bot.log.info(u'Intializing PurchaseBot')

    halt_on_new_gid = False
    reset_gid = False

    purchasebot = bot.PurchaseBot(
        data_path='nin.json',
        pickle_path='session.pickle'
    )

    purchasebot.init_bot()

    gid = purchasebot.session.cookies.get(
        'shoppingCartGID',
        domain='store.steampowered.com'
    )

    bot.log.info(u'Current shoppingCartGID is: {0}'.format(gid))

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

    random_products = [random.choice(products) for x in xrange(50)]
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

        received_new_gid = 'shoppingCartGID' in req.headers.get(
            'Set-Cookie',
            ''
        )

        if received_new_gid:
            bot.log.info(u'** Received a new shoppingCartGID **')

            bot.log.info(
                u'Current shoppingCartGID is {0}'.format(
                    purchasebot.session.cookies.get('shoppingCartGID')
                )
            )

            purchasebot.save_session_to_file()

            if halt_on_new_gid:
                bot.log.info(u'Received a new gid, halting')

                break

        count += 1

    # purchasebot.cart_checkout(clear_shopping_cart=False)
