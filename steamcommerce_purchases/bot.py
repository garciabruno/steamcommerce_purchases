#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import os
import sys
import time
import json
import pickle
import logging

import steam.guard
import steam.webauth
from totp import SteamTOTP


log = logging.getLogger('[SteamCommerce Purchases]')

log.setLevel(logging.DEBUG)
format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

ch = logging.StreamHandler(sys.stdout)
fh = logging.FileHandler('logs/purchases.log')

ch.setFormatter(format)
fh.setFormatter(format)

log.addHandler(ch)
log.addHandler(fh)


class PurchaseBot(object):
    def __init__(self):
        self.REQUESTS_DEBUG = True

    def debug_html_to_file(self, filename, content):
        f = open(os.path.join('debug', filename), 'wb+')
        f.write(content.encode('utf-8'))
        f.close()

    def get_json_from_file(self, pathname):
        f = open(pathname, 'r')
        raw = f.read()
        f.close()

        data = json.loads(raw)
        self.data = data

        return data

    def init_session_from_file(self, filename):
        f = open(filename, 'r')
        session = pickle.load(f)
        f.close()

        self.session = session

        return session

    def save_session_to_file(self):
        f = open('session.pickle', 'wb+')
        pickle.dump(self.session, f)
        f.close()

    def session_is_logged_in(self, account_name):
        req = self.session.get('http://store.steampowered.com')

        if req.status_code != 200:
            log.debug(u'Did not receive 200 from store')

            return False

        return account_name in req.text

    def get_cookies_from_file(self, filename):
        cookies = {}

        f = open(filename, 'r')
        lines = f.readlines()
        f.close()

        for line in lines:
            split = line.rsplit('=')
            cookies[split[0]] = split[1].replace('\n', '')[:-1]

        return cookies

    def generate_twofactor_code(self, shared_secret):
        # return steam.guard.generate_twofactor_code(shared_secret)

        totp = SteamTOTP(shared_secret=shared_secret)

        return totp.generateLoginToken()

    def init_session(self, data):
        log.debug(u'Intializing session')

        twofactor_code = self.generate_twofactor_code(data['shared_secret'])

        log.debug(u'Got twofactor_code {0}'.format(twofactor_code))

        user = steam.webauth.WebAuth(data['account_name'], data['password'])
        session = user.login(twofactor_code=twofactor_code)

        log.debug(u'Logged in, retrieving store.steampowered.com')

        session.get('http://store.steampowered.com')
        session.get('https://store.steampowered.com')

        self.session = session

        log.debug(u'Session is set')

        log.debug(u'Saving session to file')

        self.save_session_to_file()

        return session

    def add_subid_to_cart(self, subid):
        req = self.session.post(
            'http://store.steampowered.com/cart/',
            data={
                'sessionid': self.session.cookies.get(
                    'sessionid',
                    domain='store.steampowered.com'
                ),
                'action': 'add_to_cart',
                'subid': '%s' % subid
            }
        )

        return req

    def get_shopping_cart_gid(self):
        return self.session.cookies.get('shoppingCartGID')

    def get_cart_checkout(self):
        log.debug(u'GET /checkout?purchasetype=gift')

        req = self.session.get(
            'https://store.steampowered.com/checkout/?purchasetype=gift'
        )

        if req.status_code != 200:
            log.error(
                u'GET /checkout/ FAILED. STATUS CODE {0}'.format(
                    req.status_code
                )
            )

            return (False, req.status_code)

        if self.REQUESTS_DEBUG:
            self.debug_html_to_file(
                '%s_cart_checkout.html' % int(time.time()),
                req.text
            )

        return (True, req)

    def post_init_transaction(self, giftee_account_id, country_code='AR'):
        if not self.get_shopping_cart_gid():
            log.error(u'Tried to init transaction without shoppingCartGID')

            return (False, 1)

        log.debug(
            u'/inittransaction/ with shoppingCartGID {0}'.format(
                self.get_shopping_cart_gid()
            )
        )

        req = self.session.post(
            'https://store.steampowered.com/checkout/inittransaction/',
            data={
                'gidShoppingCart': self.get_shopping_cart_gid(),
                'gidReplayOfTransID': '-1',
                'PaymentMethod': 'steamaccount',
                'abortPendingTransactions': '0',
                'bHasCardInfo': '0',
                'CardNumber': '',
                'CardExpirationYear': '',
                'CardExpirationMonth': '',
                'FirstName': '',
                'LastName': '',
                'Address': '',
                'AddressTwo': '',
                'Country': country_code,
                'Phone': '',
                'ShippingFirstName': '',
                'ShippingLastName': '',
                'ShippingAddress': '',
                'ShippingAddressTwo': '',
                'ShippingCountry': country_code,
                'ShippingCity': '',
                'ShippingState': '',
                'ShippingPostalCode': '',
                'ShippingPhone': '',
                'bIsGift': '1',
                'GifteeAccountID': giftee_account_id,
                'GifteeEmail': '',
                'GifteeName': '',
                'GiftMessage': '',
                'Sentiment': 'Best Wishes',
                'Signature': '',
                'ScheduledSendOnDate': '0',
                'BankAccount': '',
                'BankCode': '',
                'BankIBAN': '',
                'BankBIC': '',
                'bSaveBillingAddress': '1',
                'gidPaymentID': '',
                'bUseRemainingSteamAccount': '1',
                'bPreAuthOnly': 0
            }
        )

        if req.status_code != 200:
            log.error(
                u'POST inittransaction FAILED. STATUS CODE {0}'.format(
                    req.status_code
                )
            )

            return (False, req.status_code)

        try:
            trans_json = req.json()
        except ValueError:
            log.error(u'Could not jsonify response')

            return (False, 2)

        transid = trans_json.get('transid')

        if not transid:
            log.error(u'Did not receive transid from response')

            return (False, 3)

        log.info(u'Created transactionid {0}'.format(transid))

        if self.REQUESTS_DEBUG:
            self.debug_html_to_file(
                '%s_init_transaction.html' % int(time.time()),
                req.text
            )

        return (True, transid)

    def get_finalprice(self, transid):
        log.debug(u'GET /getfinalprice/ with transid {0}'.format(transid))

        req = self.session.get(
            'https://store.steampowered.com/checkout/getfinalprice/',
            params={
                'count': '1',
                'transid': transid,
                'purchasetype': 'gift',
                'microtxnid': '-1',
                'cart': self.get_shopping_cart_gid(),
                'gidReplayOfTransID': '-1'
            }
        )

        if req.status_code != 200:
            log.error(
                u'GET /getfinalprice/ FAILED. STATUS CODE {0}'.format(
                    req.status_code
                )
            )

            return (False, req.status_code)

        try:
            final_json = req.json()
        except ValueError:
            log.error(u'Could not jsonify response')

            return (False, 1)

        success = final_json.get('success')

        if not success:
            log.info('Get final price failed. Aborting')

            return (False, 2)

        log.info(
            u'Received success from getfinalprice: {0}'.format(
                final_json
            )
        )

        if self.REQUESTS_DEBUG:
            self.debug_html_to_file(
                '%s_get_final_price.html' % int(time.time()),
                req.text
            )

        return (True, final_json)

    def finalize_transaction(self, transid):
        log.debug(
            u'POST /finalizetransaction/ with transid {0}'.format(
                transid
            )
        )

        req = self.session.post(
            'https://store.steampowered.com/checkout/finalizetransaction/',
            data={
                'transid': transid,
                'CardCVV2': ''
            }
        )

        if req.status_code != 200:
            log.error(
                u'POST /finalizetransaction/ FAILED. STATUS CODE {0}'.format(
                    req.status_code
                )
            )

            return (False, req.status_code)

        log.info(
            u'Received success from finalizetransaction: {0}'.format(
                req.text
            )
        )

        if self.REQUESTS_DEBUG:
            self.debug_html_to_file(
                '%s_finilize_transaction.html' % int(time.time()),
                req.text
            )

        return (True, req.text)

    def transaction_status(self, transid):
        log.debug(
            u'POST /transactionstatus/ with transid {0}'.format(
                transid
            )
        )

        req = self.session.get(
            'https://store.steampowered.com/checkout/transactionstatus/',
            params={
                'count': '1',
                'transid': transid
            }
        )

        if req.status_code != 200:
            log.error(
                u'GET /transactionstatus/ FAILED. STATUS CODE {0}'.format(
                    req.status_code
                )
            )

            return (False, req.status_code)

        log.info(
            u'Received success from transactionstatus: {0}'.format(
                req.text
            )
        )

        if self.REQUESTS_DEBUG:
            self.debug_html_to_file(
                '%s_transaction_status.html' % int(time.time()),
                req.text
            )

        return (True, req.text)

    def cart_checkout(self, clear_shopping_cart=True):
        log.info(u'Intializing cart checkout')

        self.get_cart_checkout()

        transaction_init = self.post_init_transaction('75266254')

        if not transaction_init[0]:
            return (False, transaction_init)

        transid = transaction_init[1]

        transaction_price = self.get_finalprice(transid)

        if not transaction_price[0]:
            return (False, transaction_price)

        transaction_finalize = self.finalize_transaction(transid)

        if not transaction_finalize[0]:
            return (False, transaction_finalize)

        transaction_status = self.transaction_status(transid)

        if not transaction_status[0]:
            return (False, transaction_status)

        if clear_shopping_cart:
            self.session.set('shoppingCartGID', None)

            self.session.set(
                'shoppingCartGID', None, domain='store.steampowered.com'
            )

            self.save_session_to_file()

        return True
