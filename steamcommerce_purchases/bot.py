#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import os
import re
import time
import json
import pickle
import urllib
import requests

import steam.guard
import steam.webauth

import logger
from totp import SteamTOTP


log = logger.Logger('SteamCommerce Purchases', 'purchases.log').get_logger()


class PurchaseBot(object):
    def __init__(self, data_path=None, pickle_path=None, USE_TWO_FACTOR=True):
        self.data_path = data_path
        self.pickle_path = pickle_path
        self.REQUESTS_DEBUG = False
        self.USE_TWO_FACTOR = USE_TWO_FACTOR

    def init_bot(self):
        if not self.data_path:
            raise Exception('No json data file found')

        data = self.get_json_from_file(self.data_path)

        if not os.path.isfile(self.pickle_path):
            self.init_session(data)
        else:
            log.info(u'Initiliazing session from pickle')
            self.init_session_from_file(self.pickle_path)
            log.info(u'Checking if session is still logged in')

            if not self.session_is_logged_in(data['account_name']):
                log.info(u'Session got logged out! Re-logging in...')
                self.init_session(data)
            else:
                log.info(u'Session is still logged in')

        log.info(u'Getting account store region')
        region = self.get_store_region()

        if not region:
            log.error(u'Could not retrieve store region')
        else:
            log.info(u'Current store region is: {0}'.format(region))

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
        f = open(self.pickle_path, 'wb+')
        pickle.dump(self.session, f)
        f.close()

    def session_is_logged_in(self, account_name):
        req = self.session.get('http://store.steampowered.com')

        if req.status_code != 200:
            log.error(u'Did not receive 200 from store')

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
        log.info(u'Intializing session')

        if self.USE_TWO_FACTOR:
            twofactor_code = self.generate_twofactor_code(data['shared_secret'])
            log.info(u'Got twofactor_code {0}'.format(twofactor_code))

            user = steam.webauth.WebAuth(data['account_name'], data['password'])
            session = user.login(twofactor_code=twofactor_code)
        else:
            user = steam.webauth.WebAuth(data['account_name'], data['password'])
            session = user.login()

        log.info(u'Logged in, retrieving store.steampowered.com')

        session.get('http://store.steampowered.com')
        session.get('https://store.steampowered.com')

        self.session = session

        log.info(u'Session is set')
        log.info(u'Saving session to file')

        self.save_session_to_file()

        return session

    def debug_html_to_file(self, filename, content):
        f = open(os.path.join('debug', filename), 'wb+')
        f.write(content.encode('utf-8'))
        f.close()

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
            log.error(
                u'Did not receive transid from response. Not enough balance?'
            )

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

            return (False, 4)

        success = final_json.get('success')

        if not success:
            log.info('Get final price failed. Aborting')

            return (False, 5)

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

    def cart_checkout(self, giftee_account_id, clear_shopping_cart=True):
        log.info(u'Intializing cart checkout')

        self.get_cart_checkout()

        transaction_init = self.post_init_transaction(giftee_account_id)

        if not transaction_init[0]:
            return {
                'success': False,
                'status': transaction_init[1]
            }

        transid = transaction_init[1]
        transaction_price = self.get_finalprice(transid)

        if not transaction_price[0]:
            return {
                'sucess': False,
                'status': transaction_price[1]
            }

        transaction_finalize = self.finalize_transaction(transid)

        if not transaction_finalize[0]:
            return {
                'sucess': False,
                'status': transaction_finalize[1]
            }

        transaction_status = self.transaction_status(transid)

        if not transaction_status[0]:
            return {
                'success': False,
                'status': transaction_status[1]
            }

        if clear_shopping_cart:
            self.session.cookies.set(
                'shoppingCartGID',
                None,
                domain='store.steampowered.com'
            )

            self.save_session_to_file()

        return {'success': True}

    def verify_account_email(self, token):
        req = self.session.get(
            'https://steamcommunity.com/actions/validateemail',
            params={
                'stoken': token
            }
        )

        if req.status_code != 200:
            return None

        try:
            req.json()
        except ValueError:
            return None

        return 'Success!' in req.text

    def validate_phone_number(self, phone_number):
        # Format must be '+54+351xxxxxxx'

        req = self.session.get(
            'https://store.steampowered.com/phone/validate',
            params='phoneNumber={0}'.format(phone_number)
        )

        if req.status_code != 200:
            return None

        try:
            req.json()
        except ValueError:
            return None

        data = req.json()

        return data['success'] and data['is_valid']

    def add_phone_number(self, phone_number):
        req = self.session.get(
            'https://store.steampowered.com//phone/add_ajaxop',
            params={
                'op': 'get_phone_number',
                'input': phone_number,
                'sessionID': self.session.cookies.get(
                    'sessionid',
                    domain='store.steampowered.com'
                ),
                'confirmed': 1,
                'checkfortos': 1,
                'bisediting': 0
            }
        )

        if req.status_code != 200:
            return None

        try:
            req.json()
        except ValueError:
            return None

        data = req.json()

        return data['success'] and data['state'] == 'get_sms_code'

    def confirm_sms_code(self, sms_code):
        req = requests.get(
            'https://store.steampowered.com//phone/add_ajaxop',
            params={
                'op': 'get_sms_code',
                'input': sms_code,
                'sessionID': self.session.cookies.get(
                    'sessionid',
                    domain='store.steampowered.com'
                ),
                'confirmed': 1,
                'checkfortos': 1,
                'bisediting': 0
            }
        )

        if req.status_code != 200:
            return None

        try:
            req.json()
        except ValueError:
            return None

        data = req.json()

        return data['success'] and data['state'] == 'done'

    def add_funds(self, amount, method='bitcoin', country='AR', currency='USD'):
        req = self.session.post(
            'http://store.steampowered.com/steamaccount/addfundssubmit',
            data={
                'action': 'add_to_cart',
                'amount': amount,
                'currency': currency,
                'mtreturnurl': '',
                'sessionID': self.session.cookies.get(
                    'sessionid',
                    domain='store.steampowered.com'
                )
            }
        )

        matches = re.findall(
            r'cart=([0-9]+)',
            urllib.unquote(req.url),
            re.DOTALL
        )

        if not len(matches):
            return False

        cart_gid = matches[0]

        req = self.session.post(
            'https://store.steampowered.com/checkout/inittransaction/',
            data={
                'Address': '',
                'AddressTwo': '',
                'BankAccount': '',
                'BankBIC': '',
                'BankCode': '',
                'BankIBAN': '',
                'CardExpirationMonth': '',
                'CardExpirationYear': '',
                'CardNumber': '',
                'City': '',
                'Country': country,
                'FirstName': '',
                'GiftMessage': '',
                'GifteeAccountID': 0,
                'GifteeEmail': '',
                'GifteeName': '',
                'LastName': '',
                'PaymentMethod': method,
                'Phone': '',
                'PostalCode': '',
                'ScheduledSendOnDate': 0,
                'Sentiment': '',
                'ShippingAddress': '',
                'ShippingAddressTwo': '',
                'ShippingCity': '',
                'ShippingCountry': country,
                'ShippingFirstName': '',
                'ShippingLastName': '',
                'ShippingPhone': '',
                'ShippingPostalCode': '',
                'ShippingState': '',
                'Signature': '',
                'State': '',
                'abortPendingTransactions': 0,
                'bHasCardInfo': 0,
                'bIsGift': 0,
                'bPreAuthOnly': 0,
                'bSaveBillingAddress': 1,
                'bUseRemainingSteamAccount': 0,
                'gidPaymentID': '',
                'gidReplayOfTransID': -1,
                'gidShoppingCart': cart_gid,
            }
        )

        if req.status_code != 200:
            return False

        try:
            data = req.json()
        except ValueError:
            return False

        if not data['success']:
            return False

        transid = data['transid']

        req = self.session.get(
            'https://store.steampowered.com/checkout/getfinalprice/',
            params={
                'count': 1,
                'transid': transid,
                'purchasetype': 'self',
                'microtxnid': -1,
                'cart': cart_gid,
                'gidReplayOfTransID': -1
            }
        )

        if req.status_code != 200:
            return False

        try:
            data = req.json()
        except ValueError:
            return False

        if not data['success']:
            return False

        req = self.session.get(
            'https://store.steampowered.com/checkout/externallink/',
            params={
                'transid': transid
            }
        )

        if method != 'bitcoin':
            return req.url

        matches = re.findall(
            'action="(https://bitpay.com.*?)"',
            req.text,
            re.DOTALL
        )

        if not len(matches):
            return False

        return matches[0]

    def get_store_region(self):
        req = self.session.get('https://store.steampowered.com/account/')

        if req.status_code != 200:
            return False

        matches = re.findall(
            '<span class="account_data_field">(.*?)</span>',
            req.text,
            re.DOTALL
        )

        if not len(matches):
            return False

        return matches[0]


class RegisterBot(object):
    def __init__(self, account_name, password, email):
        self.account_name = account_name
        self.password = password
        self.email = email

    def check_availability(self):
        req = requests.get(
            'https://store.steampowered.com/join/checkavail/',
            params={
                'accountname': self.account_name,
                'count': 1
            }
        )

        if req.status_code != 200:
            return None

        try:
            req.json()
        except ValueError:
            return None

        return req.json()['bAvailable']

    def get_register_page(self):
        return requests.get('https://store.steampowered.com/join/')

    def get_captcha_from_register(self, request):
        matches = re.findall(
            r'captcha\.php\?gid=([0-9]+)',
            request.text,
            re.DOTALL
        )

        if not len(matches):
            return None

        return matches[0]

    def verify_captcha(self, captcha_gid, captcha_text):
        req = requests.get(
            'https://store.steampowered.com/join/verifycaptcha/',
            params={
                'captchagid': captcha_gid,
                'captcha_text': captcha_text,
                'email': self.email,
                'count': 22
            }
        )

        if req.status_code != 200:
            return None

        try:
            req.json()
        except ValueError:
            return None

        return req.json()['bCaptchaMatches']

    def create_account(self, captcha_gid, captcha_text):
        req = requests.post(
            'https://store.steampowered.com/join/createaccount/',
            data={
                'accountname': self.account_name,
                'captcha_text': captcha_text,
                'captchagid': captcha_gid,
                'count': 22,
                'email': self.email,
                'i_agree': 1,
                'password': self.password,
                'ticket': ''
            }
        )

        if req.status_code != 200:
            return None

        try:
            req.json()
        except ValueError:
            return None

        return req.json()['bSuccess']
