#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import os
import re
import json
import pickle
import urllib
import requests

import steam.guard
import steam.webauth

import logger
from totp import SteamTOTP

import enums
import controller


log = logger.Logger('Bot', 'purchases.log').get_logger()


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
            twofactor_code = self.generate_twofactor_code(
                data['shared_secret']
            )

            log.info(u'Got twofactor_code {0}'.format(twofactor_code))

            user = steam.webauth.WebAuth(
                data['account_name'],
                data['password']
            )

            session = user.login(twofactor_code=twofactor_code)
        else:
            user = steam.webauth.WebAuth(
                data['account_name'],
                data['password']
            )

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
        log.info(
            u'Adding subid {0} to cart with gid: {1}'.format(
                subid,
                self.get_shopping_cart_gid()
            )
        )

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

        item_added = 'YOUR ITEM\'S BEEN ADDED!' in req.text

        if not item_added:
            log.error(u'Failed to add subid {0} to cart'.format(subid))
        else:
            self.save_session_to_file()
            log.info(u'Succesfuly added subid {0} to cart'.format(subid))

        return req

    def remove_gid_from_cart(self, item_gid):
        log.info(u'Removing cart item gid {0} from cart'.format(item_gid))

        req = self.session.post(
            'https://store.steampowered.com/cart/',
            data={
                'sessionid': self.session.cookies.get(
                    'sessionid',
                    domain='store.steampowered.com'
                ),
                'action': 'remove_line_item',
                'cart': self.get_shopping_cart_gid(),
                'lineitem_gid': item_gid
            }
        )

        item_removed = 'YOUR ITEM HAS BEEN REMOVED!' in req.text

        if not item_removed:
            log.error(
                u'Failed to remove cart item gid {0} from cart'.format(
                    item_gid
                )
            )
        else:
            self.save_session_to_file()

            log.info(
                u'Succesfuly removed item gid {0} from cart'.format(
                    item_gid
                )
            )

        return req

    def get_shopping_cart_gid(self):
        return self.session.cookies.get('shoppingCartGID')

    def get_cart_checkout(self):
        log.info(u'Getting cart checkout')

        req = self.session.get(
            'https://store.steampowered.com/checkout/?purchasetype=gift'
        )

        if req.status_code != 200:
            log.error(
                u'Cart checkout received status code {}'.format(
                    req.status_code
                )
            )

            return enums.EPurchaseResult.GetCartCheckoutFailed

        return req

    def post_init_transaction(self, giftee_account_id, country_code):
        if not self.get_shopping_cart_gid():
            log.error(u'Tried to init transaction without shoppingCartGID')

            return enums.ECartResult.DidNotFindShoppingCartGid

        log.info(
            u'Posting init transaction with shoppingCartGID {0}'.format(
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
                u'Init transaction received status code {0}'.format(
                    req.status_code
                )
            )

            return enums.EPurchaseResult.PostInitTransactionFailed

        try:
            response = req.json()
        except ValueError:
            log.error(u'Could not serialize response')
            return enums.EPurchaseResult.CouldNotJSONResponse
        except Exception, e:
            log.error(u'Raised unknown Exception: {0}'.format(e))
            return enums.EPurchaseResult.RaisedUnknownException

        if not response.get('success'):
            log.error(
                u'Did not receive success from response. Not enough balance?'
            )

            return enums.EPurchaseResult.ResponseDidNotContainSuccess

        if not response.get('transid'):
            log.error(
                u'Did not receive transid from response. Not enough balance?'
            )

            return enums.EPurchaseResult.ResponseDidNotContainTransId

        transid = response.get('transid')
        log.info(u'Received transid {0}'.format(transid))

        return transid

    def get_finalprice(self, transid):
        log.info(u'Getting get final price with transid {0}'.format(transid))

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
                u'Get final price received status code {0}'.format(
                    req.status_code
                )
            )

            return enums.EPurchaseResult.GetFinalPriceFailed

        try:
            response = req.json()
        except ValueError:
            log.error(u'Could not serialize response')
            return enums.EPurchaseResult.CouldNotJSONResponse
        except Exception, e:
            log.error(u'Raised unknown Exception: {0}'.format(e))
            return enums.EPurchaseResult.RaisedUnknownException

        if not response.get('success'):
            log.error(
                u'Did not receive success from response. Not enough balance?'
            )

            return enums.EPurchaseResult.ResponseDidNotContainSuccess

        if response.get('total') > response.get('steamAccountBalance'):
            log.error(u'Not enough balance found in final price')

            log.error(
                u'Total: {0} AccountTotal: {1} AccountBalance: {2}'.format(
                    response.get('total'),
                    response.get('steamAccountTotal'),
                    response.get('steamAccountBalance')
                )
            )

            return enums.EPurchaseResult.InsufficientFunds

        return req

    def finalize_transaction(self, transid):
        log.info(
            u'Posting finalize transaction with transid {0}'.format(
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
                u'Finalize transaction received status code {0}'.format(
                    req.status_code
                )
            )

            return enums.EPurchaseResult.PostFinalizeTransactionFailed

        try:
            response = req.json()
        except ValueError:
            log.error(u'Could not serialize response')
            return enums.EPurchaseResult.CouldNotJSONResponse
        except Exception, e:
            log.error(u'Raised unknown Exception: {0}'.format(e))
            return enums.EPurchaseResult.RaisedUnknownException

        if response.get('success') != 22:
            if response.get('success') == 1:
                # Maybe the backend responded faster than we expected
                # and there *shouldn't* be a reason to poll transactionstatus

                return req

            log.error(
                u'Received unknown success status: {0}'.format(
                    response.get('success')
                )
            )

            return enums.EPurchaseResult.RaisedUnknownException

        return req

    def transaction_status(self, transid):
        log.info(
            u'Getting transaction status with transid {0}'.format(
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
                u'Transaction status received status code {0}'.format(
                    req.status_code
                )
            )

            return enums.EPurchaseResult.GetTransactionStatusFailed

        try:
            response = req.json()
        except ValueError:
            log.error(u'Could not serialize response')
            return enums.EPurchaseResult.CouldNotJSONResponse
        except Exception, e:
            log.error(u'Raised unknown Exception: {0}'.format(e))
            return enums.EPurchaseResult.RaisedUnknownException

        return response.get('success')

    def cart_checkout(self, giftee_account_id, country_code):
        log.info(
            u'Intializing cart checkout to giftee account id {0}'.format(
                giftee_account_id
            )
        )

        self.get_cart_checkout()  # Start a call just to fake things up
        transid = self.post_init_transaction(giftee_account_id, country_code)

        if isinstance(transid, enums.EPurchaseResult):
            return transid

        transaction_price = self.get_finalprice(transid)

        if isinstance(transaction_price, enums.EPurchaseResult):
            return transaction_price

        transaction_finalize = self.finalize_transaction(transid)

        if isinstance(transaction_finalize, enums.EPurchaseResult):
            return transaction_finalize

        transaction_status = 22  # Set initial status as "PENDING"
        attemps = 25

        while transaction_status == 22 and attemps > 0:
            # Start polling on transaction status until its either "1" or an
            # EPurchaseResult

            transaction_status = self.transaction_status(transid)

            if isinstance(transaction_status, enums.EPurchaseResult):
                return transaction_status

            attemps -= 1

        if transaction_status == 22 and attemps <= 0:
            return enums.EPurchaseResult.ReachedMaximumPollAttemps

        self.session.cookies.set(
            'shoppingCartGID',
            None,
            domain='store.steampowered.com'
        )

        self.save_session_to_file()

        return enums.EPurchaseResult.Succeded

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

    def add_funds(
        self,
        amount,
        method='bitcoin',
        country='AR',
        currency='USD'
    ):
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

    def get_store_region(self, req=None):
        if not req:
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

    def get_account_balance(self, req=None):
        if not req:
            req = self.session.get('https://store.steampowered.com')

        if req.status_code != 200:
            return False

        matches = re.findall(
            '<a class="global_action_link" id="header_wallet_balance" href="https://store.steampowered.com/account/store_transactions/">(.*?)</a>',
            req.text,
            re.DOTALL
        )

        if not len(matches):
            return False

        return matches[0]

    def get_cart_count(self, req=None):
        if not req:
            req = self.session.get('https://store.steampowered.com')

        matches = re.findall(
            '<span id="cart_item_count_value">([0-9]+)</span>',
            req.text,
            re.DOTALL
        )

        if not len(matches):
            return 0

        return int(matches[0])

    def sync_data(self, bot_id, req=None):
        if not req:
            req = self.session.get('https://store.steampowered.com')

        account_balance = self.get_account_balance(req=req)
        cart_count = self.get_cart_count(req=req)

        data = {
            'id': bot_id,
            'account_balance': account_balance if account_balance else None,
            'current_cart_count': cart_count
        }

        return controller.BotController().update(**data)


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


def get_purchasebot(bot_obj):
    if bot_obj.current_state != enums.EBotState.StandingBy:
        return enums.EBotResult.NotBotAvailableFound

    purchasebot = PurchaseBot(
        data_path=os.path.join(
            os.getcwd(), 'data', bot_obj.data_filename
        ),
        pickle_path=os.path.join(
            os.getcwd(), 'data', bot_obj.session_filename
        )
    )

    purchasebot.init_bot()

    return purchasebot
