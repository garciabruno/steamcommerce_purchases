#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import os
import json
import time
import pickle
import base64

from core import items
from core import enums
from core import logger

import steam.guard
import steam.webauth

log = logger.Logger('steamcommerce.purchases', 'steamcommerce.purchases.log').get_logger()


class WebAccount(object):
    def __init__(self, network_id):
        self.data_path = os.path.join('data', '{}.json'.format(network_id))
        self.pickle_path = os.path.join('data', '{}.pickle'.format(network_id))

        data = self.get_data_from_file(self.data_path)

        self.account_name = data.get('account_name')
        self.password = data.get('password')
        self.shared_secret = data.get('shared_secret')

        self.use_2fa = False

        if self.shared_secret:
            self.use_2fa = True

        if os.path.exists(self.pickle_path):
            self.init_session_from_file()
        else:
            self.init_session()

        if not self.session_is_logged_in():
            self.init_session()

        self.set_cart_count()

    def init_session(self):
        log.info(
            u'Initializing session for account_name {0}. USE 2FA: {1}'.format(
                self.account_name,
                'YES' if self.use_2fa else 'NO'
            )
        )

        user = steam.webauth.WebAuth(self.account_name, self.password)

        if self.use_2fa:
            log.info(u'Generating 2FA Code for {}'.format(self.account_name))

            twofactor_code = self.generate_two_factor_code()

            log.info(u'Received 2FA code {}'.format(twofactor_code))
            log.info(u'Logging into account {}'.format(self.account_name))

            session = user.login(twofactor_code=twofactor_code)
        else:
            log.info(u'Logging into account {}'.format(self.account_name))
            session = user.login()

        log.info(u'Logged in, getting store sites for cookie setting')

        session.get('http://store.steampowered.com')
        session.get('https://store.steampowered.com')

        self.session = session
        self.save_session_to_file()

        log.info(u'Session for account name {} has been set'.format(self.account_name))

        return True

    def save_session_to_file(self):
        f = open(self.pickle_path, 'wb+')
        pickle.dump(self.session, f)
        f.close()

    def init_session_from_file(self):
        f = open(self.pickle_path, 'r')
        session = pickle.load(f)
        f.close()

        self.session = session

    def session_is_logged_in(self):
        log.info(u'Checking if account is still logged for {}'.format(self.account_name))

        req = self.session.get('https://store.steampowered.com')

        if req.status_code != 200:
            return False

        return self.account_name in req.text

    def get_steam_id_from_cookies(self):
        return self.session.cookies.get('steamLogin', domain='steamcommunity.com').rsplit('%7C')[0]

    def generate_two_factor_code(self):
        return steam.guard.generate_twofactor_code_for_time(
            base64.b64decode(self.shared_secret),
            time.time()
        )

    def get_data_from_file(self, path):
        f = open(os.path.join(os.getcwd(), path), 'r')
        raw = f.read()
        f.close()

        return json.loads(raw)

    def get_cart_object(self, req=None):
        if not req:
            req = self.session.get('https://store.steampowered.com/cart')

        if req.status_code != 200:
            return enums.EWebAccountResult.Failed

        cart_results = items.SteamCart.all_from(req.text)

        if not len(cart_results):
            return enums.EWebAccountResult.CrawlerFailed

        return cart_results[0]

    def get_cart_count(self, req=None):
        log.info(u'Getting current cart count for {}'.format(self.account_name))

        cart_object = self.get_cart_object(req=req)

        if type(cart_object) == enums.EWebAccountResult:
            log.error(u'Failed to retrieve current cart count')

            return cart_object

        return int(cart_object.count or 0)

    def set_cart_count(self, req=None):
        cart_count = self.get_cart_count(req=req)

        if type(cart_count) != enums.EWebAccountResult:
            self.cart_count = cart_count

    def get_shopping_cart_gid(self):
        return self.session.cookies.get('shoppingCartGID', domain='store.steampowered.com')

    def get_session_id(self, domain):
        return self.session.cookies.get('sessionid', domain=domain)

    def subid_was_added(self, req):
        cart_object = self.get_cart_object(req=req)

        text_added = cart_object.cart_status_message == 'YOUR ITEM\'S BEEN ADDED!'
        count_is_bigger = cart_object.count > self.cart_count

        return text_added and count_is_bigger

    def add_subid_to_cart(self, subid):
        log.info(u'Adding subid {0} to cart {1}'.format(subid, self.get_shopping_cart_gid()))

        try:
            req = self.session.post(
                'http://store.steampowered.com/cart/',
                data={
                    'sessionid': self.get_session_id('store.steampowered.com'),
                    'action': 'add_to_cart',
                    'subid': str(subid)
                }
            )
        except Exception, e:
            log.error(u'Failed to add subid {0} to cart. Raised {1}'.format(subid, e))

            return enums.EWebAccountResult.UnknownException

        if req.status_code != 200:
            return enums.EWebAccountResult.Failed

        if not self.subid_was_added(req):
            return enums.ECartResult.Failed

        if self.cart_is_gifteable(req):
            return enums.ECartResult.CartNotGifteable

        self.set_cart_count(req=req)

        return enums.ECartResult.Added
