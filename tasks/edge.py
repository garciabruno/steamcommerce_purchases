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
def get_external_link_from_transid(self, network_id, transid):
    edge_bot = bot.EdgeBot(network_id)
    response = edge_bot.web_account.get_external_link_from_transid(transid)

    return response
