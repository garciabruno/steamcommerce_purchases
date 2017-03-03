#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from core import bot
from tasks import app


@app.app.task(bind=True)
def add_subids_to_cart(self, network_id, items):
    edge_bot = bot.EdgeBot(network_id)
    response = edge_bot.add_subids_to_cart(items)

    return response


@app.app.task(bind=True)
def checkout_cart(self, network_id, giftee_account_id, payment_method='steamaccount'):
    edge_bot = bot.EdgeBot(network_id)
    response = edge_bot.checkout_cart(giftee_account_id, payment_method=payment_method)

    return response


@app.app.task(bind=True)
def reset_shopping_cart(self, network_id):
    edge_bot = bot.EdgeBot(network_id)

    edge_bot.web_account.reset_shopping_cart_gid()
    edge_bot.web_account.save_session_to_file()

    return {'success': True}


@app.app.task(bind=True)
def poll_transaction_status(self, network_id, transid):
    edge_bot = bot.EdgeBot(network_id)
    response = edge_bot.web_account.poll_transaction_status(transid, times=50, delay=1)

    return response


@app.app.task(bind=True)
def get_external_link_from_transid(self, network_id, transid):
    edge_bot = bot.EdgeBot(network_id)
    response = edge_bot.web_account.get_external_link_from_transid(transid)

    # Give edge controller 60 seconds for payment to complete purchase

    poll_transaction_status.delay(network_id, transid)

    return response
