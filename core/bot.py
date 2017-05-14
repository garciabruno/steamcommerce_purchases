#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import os
import re
import json
import time
import pickle
import base64

import config

from core import items
from core import enums
from core import logger

import steam.guard
import steam.webauth
from steam.enums import EResult

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

    def get_country_code_from_cookies(self):
        return self.session.cookies.get('steamCountry', domain='steamcommunity.com').rsplit('%7C')[0]

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
        cart_object = self.get_cart_object(req=req)

        if isinstance(cart_object, enums.EWebAccountResult):
            log.error(u'Failed to retrieve current cart count')

            return cart_object

        return len(cart_object.items or [])

    def set_cart_count(self, req=None):
        cart_count = self.get_cart_count(req=req)

        if not isinstance(cart_count, enums.EWebAccountResult):
            self.cart_count = cart_count

    def get_shopping_cart_gid(self):
        return self.session.cookies.get('shoppingCartGID', domain='store.steampowered.com')

    def reset_shopping_cart_gid(self):
        return self.session.cookies.set('shoppingCartGID', None)

    def get_session_id(self, domain):
        return self.session.cookies.get('sessionid', domain=domain)

    def subid_was_added(self, req):
        cart_object = self.get_cart_object(req=req)

        text_added = cart_object.cart_status_message == 'YOUR ITEM\'S BEEN ADDED!'
        count_is_bigger = self.get_cart_count(req=req) > self.cart_count

        return text_added and count_is_bigger

    def gid_was_removed(self, req):
        cart_object = self.get_cart_object(req=req)

        text_removed = cart_object.cart_status_message == 'YOUR ITEM HAS BEEN REMOVED!'
        count_is_smaller = len(cart_object.items or []) < self.cart_count

        return text_removed and count_is_smaller

    def cart_is_gifteable(self, req):
        cart_object = self.get_cart_object(req=req)
        checkout_link = 'https://store.steampowered.com/checkout/?purchasetype=gift'

        return checkout_link in (cart_object.cart_checkout_button or '')

    def add_subid_to_cart(self, subid):
        shopping_cart_gid = self.get_shopping_cart_gid()

        log.info(u'Adding subid {0} to cart {1}'.format(subid, shopping_cart_gid))

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
            log.info(u'Checking if shoppingCartGID still exists')

            self.session.get('https://store.steampowered.com')

            self.set_cart_count(req=req)
            self.save_session_to_file()

            if not self.get_shopping_cart_gid():
                return enums.ECartResult.CartDissapeared

            if self.get_shopping_cart_gid() != shopping_cart_gid:
                return enums.ECartResult.CartReset

            return enums.ECartResult.Failed

        self.set_cart_count(req=req)
        self.save_session_to_file()

        if not self.cart_is_gifteable(req):
            return enums.ECartResult.CartNotGifteable

        return enums.ECartResult.Added

    def remove_gid_from_cart(self, gid):
        shopping_cart_gid = self.get_shopping_cart_gid()

        log.info(u'Removing item gid {0} from cart {1}'.format(gid, shopping_cart_gid))

        try:
            req = self.session.post(
                'https://store.steampowered.com/cart/',
                data={
                    'sessionid': self.get_session_id('store.steampowered.com'),
                    'action': 'remove_line_item',
                    'cart': shopping_cart_gid,
                    'lineitem_gid': gid
                }
            )
        except Exception, e:
            log.error(u'Failed to remove gif {0} from cart. Raised {1}'.format(gid, e))

            return enums.EWebAccountResult.UnknownException

        if req.status_code != 200:
            return enums.EWebAccountResult.Failed

        if not self.gid_was_removed(req):
            return enums.ECartResult.Failed

        self.set_cart_count(req=req)
        self.save_session_to_file()

        return enums.ECartResult.Removed

    def remove_last_cart_item(self):
        cart_object = self.get_cart_object()

        if not len(cart_object.items):
            return enums.ECartResult.Failed

        last_item = cart_object.items[0]
        remove_gid_matches = re.findall(r'([0-9]+)', last_item.remove_button, re.DOTALL)

        if not len(remove_gid_matches):
            return enums.ECartResult.Failed

        remove_gid = remove_gid_matches[0]

        return self.remove_gid_from_cart(remove_gid)

    def init_transaction(self, giftee_account_id, payment_method='steamaccount'):
        country_code = self.get_country_code_from_cookies()
        shopping_cart_gid = self.get_shopping_cart_gid()

        if not shopping_cart_gid:
            return enums.ETransactionResult.ShoppingCartGIDNotFound

        log.info(u'Init transaction with shoppingCartGID {}'.format(shopping_cart_gid))

        transaction_data = config.TRANSACTION_DATA

        transaction_data.update({
            'gidShoppingCart': shopping_cart_gid,
            'PaymentMethod': payment_method,
            'Country': country_code,
            'ShippingCountry': country_code,
            'GifteeAccountID': giftee_account_id
        })

        req = self.session.post(
            'https://store.steampowered.com/checkout/inittransaction/',
            data=transaction_data
        )

        if req.status_code != 200:
            log.error(u'Failed to init transaction. Status code {0} Body {1}'.format(req.status_code, req.text))

            return enums.EWebAccountResult.Failed

        try:
            data = req.json()
        except ValueError:
            log.error(u'Could not serialize {}'.format(req.text))

            return enums.EWebAccountResult.ResponseNotSerializable
        except Exception, e:
            log.error(u'Raised unknown Exception: {}'.format(e))

            return enums.EWebAccountResult.UnknownException

        if not data.get('success'):
            log.error(u'Response for init transaction was {}'.format(data))

            return enums.ETransactionResult.Fail

        # Note: if transid is -1 then too many purchases should trigger

        transid = data.get('transid')

        if not transid:
            log.error(u'Transid not found in init transaction data: {}'.format(data))

            return enums.ETransactionResult.TransIdNotFound

        log.info(u'Received transaction id {}'.format(transid))

        return transid

    def get_transaction_final_price(self, transid, payment_method='steamaccount'):
        log.info(u'Getting final price for transid {}'.format(transid))

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
            log.error(u'Failed to get transaction price. Status code {0} Body {1}'.format(req.status_code, req.text))

            return enums.EWebAccountResult.Failed

        try:
            data = req.json()
        except ValueError:
            log.error(u'Could not serialize {}'.format(req.text))

            return enums.EWebAccountResult.ResponseNotSerializable
        except Exception, e:
            log.error(u'Raised unknown Exception: {}'.format(e))

            return enums.EWebAccountResult.UnknownException

        result = EResult(data.get('success'))

        if result != EResult.OK:
            log.error(u'Response for final price is {}'.format(data))

            return enums.ETransactionResult.Fail

        if data.get('total') > data.get('steamAccountBalance') and payment_method == 'steamaccount':
            log.info(u'Insufficient funds for transid {}'.format(transid))

            return enums.ETransactionResult.InsufficientFunds

        log.info(
            u'Got final price successfully. Received ${} as final price'.format(
                data.get('total') / 100.0
            )
        )

        return enums.ETransactionResult.Success

    def finalize_transaction(self, transid):
        log.info(u'Finalizing transaction for transid {}'.format(transid))

        req = self.session.post(
            'https://store.steampowered.com/checkout/finalizetransaction/',
            data={
                'transid': transid,
                'CardCVV2': ''
            }
        )

        if req.status_code != 200:
            log.error(u'Failed to finalize transaction. Status code {0} Body {1}'.format(req.status_code, req.text))

            return enums.EWebAccountResult.Failed

        try:
            data = req.json()
        except ValueError:
            log.error(u'Could not serialize {}'.format(req.text))

            return enums.EWebAccountResult.ResponseNotSerializable
        except Exception, e:
            log.error(u'Raised unknown Exception: {}'.format(e))

            return enums.EWebAccountResult.UnknownException

        return data

    def get_transaction_status(self, transid):
        log.info(u'Getting transaction status for transid {}'.format(transid))

        req = self.session.get(
            'https://store.steampowered.com/checkout/transactionstatus/',
            params={
                'count': '1',
                'transid': transid
            }
        )

        if req.status_code != 200:
            log.error(u'Failed to get transaction status. Status code {0} Body {1}'.format(req.status_code, req.text))

            return enums.EWebAccountResult.Failed

        try:
            data = req.json()
        except ValueError:
            log.error(u'Could not serialize {}'.format(req.text))

            return enums.EWebAccountResult.ResponseNotSerializable
        except Exception, e:
            log.error(u'Raised unknown Exception: {}'.format(e))

            return enums.EWebAccountResult.UnknownException

        return data

    def get_external_link_from_transid(self, transid):
        attemps = 10
        external_link = None

        while external_link is None and attemps > 0:
            log.info(u'Getting external link for transid {0} ({1}/10) '.format(transid, attemps))

            req = self.session.get(
                'https://store.steampowered.com/checkout/externallink/',
                params={
                    'transid': transid
                }
            )

            if req.status_code != 200:
                log.error(u'Failed to get external link. Status code {0} Body {1}'.format(req.status_code, req.text))

                return enums.EWebAccountResult.Failed.value

            forms = items.ExternalForm.all_from(req.text)

            if not len(forms):
                log.error(u'Could not match any ExternalFrom from body')

                return enums.EWebAccountResult.Failed.value

            log.debug(req.text)

            external_link = forms[0].link

            if not external_link:
                attemps -= 1

                continue

            return {
                'transid': transid,
                'link': external_link,
                'shopping_cart_gid': self.get_shopping_cart_gid()
            }

        log.error(u'Finished polling but could not obtain transaction link from external link')

        return enums.EWebAccountResult.Failed.value

    def poll_transaction_status(self, transid, times=25, delay=0.5):
        result = EResult.Pending
        attemps = times

        while result != EResult.OK and attemps > 0:
            log.info(
                u'Polling transaction status for transid {0} ({1}/{2})'.format(
                    transid,
                    attemps,
                    times
                )
            )

            transaction_status = self.get_transaction_status(transid)

            if isinstance(transaction_status, enums.EWebAccountResult):
                log.error(
                    u'Failed to get transaction status for transid {0}, received {1}'.format(
                        transid,
                        repr(transaction_status)
                    )
                )

                continue

            result = EResult(transaction_status.get('success'))
            attemps -= 1

            time.sleep(delay)

        return result


class EdgeBot(object):
    def __init__(self, network_id):
        self.network_id = network_id
        self.web_account = WebAccount(network_id)

    def add_subids_to_cart(self, items):
        '''
            items:

            [
                {
                    'relation_type': 'A',
                    'relation_id': 123456,
                    'sub_id': 54029
                },
                ...
            ]

            response:

            {
                'shoppingCartGID': '12345678901234567890',
                'failed_shopping_cart_gids: ['123445678901234567890'],
                'failed_items': [
                    {
                        'relation_type': 'A',
                        'relation_id': 123456,
                        'sub_id': 88888
                    }
                ],
                'items': [
                    {
                        'relation_type': 'A',
                        'relation_id': 123456,
                        'sub_id': 54029
                    }
                ]
            }
        '''

        failed_shopping_cart_gids = []

        failed_items = []
        success_items = []

        for item in items:
            current_shopping_cart_gid = self.web_account.get_shopping_cart_gid()

            sub_id = item.get('sub_id')
            result = self.web_account.add_subid_to_cart(sub_id)

            if isinstance(result, enums.EWebAccountResult):
                log.error(u'Failed to push subid to cart, received {}'.format(repr(result)))

                continue

            if result == enums.ECartResult.Failed:
                log.info(u'Failed to add subid {} to cart'.format(sub_id))
            elif result == enums.ECartResult.CartDissapeared:
                log.info(u'Subid {} caused to dissapear'.format(sub_id))

                failed_shopping_cart_gids.append(current_shopping_cart_gid)
                failed_items.append(dict(item))

                success_items = []
            elif result == enums.ECartResult.CartNotGifteable:
                log.info(u'Subid {} caused cart to be not gifteable'.format(sub_id))

                self.web_account.remove_last_cart_item()
            elif result == enums.ECartResult.CartReset:
                log.info(u'Cart with shopping cart gid {} has been reset'.format(current_shopping_cart_gid))

                failed_shopping_cart_gids.append(current_shopping_cart_gid)
                success_items = []
            elif result == enums.ECartResult.Added:
                log.info(u'Subid {} added successfully'.format(sub_id))

                success_items.append(dict(item))

        response = {
            'failed_shopping_cart_gids': failed_shopping_cart_gids,
            'shoppingCartGID': self.web_account.get_shopping_cart_gid(),
            'failed_items': failed_items,
            'items': success_items
        }

        return response

    def checkout_cart(self, giftee_account_id, payment_method='steamaccount'):
        shopping_cart_gid = self.web_account.get_shopping_cart_gid()

        if not shopping_cart_gid:
            return enums.ETransactionResult.ShoppingCartGIDNotFound.value

        log.info(
            u'Checking out cart for network_id {0} with shoppingCartGID {1} (Payment method: {2})'.format(
                self.network_id,
                shopping_cart_gid,
                payment_method
            )
        )

        transid = self.web_account.init_transaction(
            giftee_account_id,
            payment_method=payment_method
        )

        if transid == '-1':
            log.info(u'Received transid -1, account has too many purchases in the last few hours')

            return enums.ETransactionResult.TooManyPurchases.value

        if isinstance(transid, enums.EWebAccountResult) or isinstance(transid, enums.ETransactionResult):
            log.error(u'Failed to initialize transaction, received {}'.format(repr(transid)))

            return enums.ETransactionResult.Fail.value

        transaction_final_price = self.web_account.get_transaction_final_price(
            transid,
            payment_method=payment_method
        )

        if isinstance(transaction_final_price, enums.EWebAccountResult):
            log.error(
                u'Failed to retrieve transaction final price, received {}'.format(
                    repr(transaction_final_price)
                )
            )

            return enums.ETransactionResult.Fail.value

        if transaction_final_price != enums.ETransactionResult.Success:
            log.error(
                u'Failed to retrieve transaction final price, received {}'.format(
                    repr(transaction_final_price)
                )
            )

            return transaction_final_price.value

        if payment_method == 'bitcoin':
            if transaction_final_price == enums.ETransactionResult.Success:
                return {
                    'result': EResult.OK.value,
                    'transid': transid,
                    'payment_method': payment_method,
                    'shopping_cart_gid': shopping_cart_gid
                }
            else:
                return transaction_final_price.value

        transaction_data = self.web_account.finalize_transaction(transid)

        if isinstance(transaction_data, enums.EWebAccountResult):
            log.error(
                u'Failed to finalize transaction, received {}'.format(
                    repr(transaction_data)
                )
            )

            return enums.ETransactionResult.Fail.value

        result = self.web_account.poll_transaction_status(transid, times=5)

        if result == EResult.OK:
            log.info(u'Transaction finalized successfully')

            self.cart_count = 0
            self.web_account.reset_shopping_cart_gid()

        return {
            'result': result.value,
            'transid': transid,
            'payment_method': payment_method,
            'shopping_cart_gid': shopping_cart_gid
        }
