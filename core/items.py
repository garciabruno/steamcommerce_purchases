#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import demiurge


class SteamCartItem(demiurge.Item):
    appid = demiurge.AttributeValueField(attr='data-ds-appid', selector='div.cart_row')
    packageid = demiurge.AttributeValueField(attr='data-ds-packageid', selector='div.cart_row')
    title = demiurge.TextField(selector='div.cart_item_desc a:first')
    price = demiurge.TextField(selector='div.cart_item_price div.price:last')
    remove_button = demiurge.AttributeValueField(attr='href', selector='a.remove_link')

    class Meta:
        selector = 'div.cart_row'


class SteamCart(demiurge.Item):
    count = demiurge.TextField(selector='span#cart_item_count_value')
    subtotal = demiurge.TextField(selector='div#cart_price_total')
    balance = demiurge.TextField(selector='a#header_wallet_balance')

    cart_status_message = demiurge.TextField(selector='div.cart_status_message')
    cart_checkout_button = demiurge.AttributeValueField(selector='a.continue:eq(0)', attr='href')

    items = demiurge.RelatedItem(SteamCartItem, selector='div.cart_item_list')
