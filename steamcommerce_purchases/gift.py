#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import re
import config
import datetime

import gmail
import urllib

from steamcommerce_api.api import logger
from steamcommerce_api.api import message
from steamcommerce_api.api import userrequest
from steamcommerce_api.api import paidrequest
from steamcommerce_api.api import notification

log = logger.Logger('SteamCommerce Email', 'gift.emails.log').get_logger()

OWNER_ID = 1

GIFT_TITLE_REGEX = r'(of the game|del juego)(.*)(on Steam|en Steam)'
GIFT_LINK_REGEX = r'(https:\/\/store\.steampowered\.com\/account\/ackgift\/.*?\?redeemer=.*)\r\n\r\nIf'
GIFT_OWNER_REGEX = r'Hello,\r\n\r\nYour friend (.*?) \(.*?\)'
GIFT_LINK_UNQUOTED = r'https://store\.steampowered\.com/account/ackgift/.*\?redeemer=(.*)'
REDEMER_REQUEST_REGEX = r'([0-9]+)(A|C)([0-9]+)'


DEFAULT_REQUEST_MESSAGE = u'''
Hola, Hemos procesado su pedido. Tu código/link de activación para el producto {0} es:\n\n{1}\n\n

****
Si tienes la intención de regalar este producto por favor no abras el enlace
en tu navegador, ya que causará que el enlace deje de ser válido.

Para regalarlo a un amigo simplemente envía el link a quien desees y que lo
abra en su navegador.
****
'''


class Email(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def get_unread_mails(self):
        log.info('Logging into {}'.format(self.username))
        g = gmail.login(self.username, self.password)
        mails = g.inbox().mail(sender='noreply@steampowered.com', unread=True)

        if len(mails) < 1:
            log.info('No unread mail found. Try again?')

            return []

        return mails

    def find_gift_emails(self):
        mails = self.get_unread_mails()

        for mail in mails:
            mail.fetch()

            gift_titles = re.findall(
                GIFT_TITLE_REGEX,
                mail.subject.replace('\r\n', ''),
                re.DOTALL
            )

            if len(gift_titles) == 0:
                log.info('Did not find any unread Steam Gift email')

                continue

            gift_links = re.findall(GIFT_LINK_REGEX, mail.body, re.DOTALL)
            owners = re.findall(GIFT_OWNER_REGEX, mail.body, re.DOTALL)

            if len(gift_links) == 0:
                log.info('Did not find any gift link')

                continue

            if len(owners) == 0:
                log.info('Did not find owner, setting to ExtremeBot')

                owners = ['ExtremeBot']

            gift_link = gift_links[0]
            unquoted_link = urllib.unquote(gift_link)

            redeemer = re.findall(GIFT_LINK_UNQUOTED, unquoted_link, re.DOTALL)

            if not len(redeemer):
                log.error(u'Unable to parse email from unquoted link')

                continue

            request_data_matches = re.findall(
                REDEMER_REQUEST_REGEX,
                redeemer[0],
                re.DOTALL
            )

            if not len(request_data_matches):
                log.error(u'Could not retrieve request data from redeemer')

                continue

            request_data = request_data_matches[0]

            log.info(
                u'Found gift link for relation {0} in request {1}-{2}'.format(
                    request_data[0],
                    request_data[1],
                    request_data[2]
                )
            )

            data = {
                'user': OWNER_ID,
                'date': datetime.datetime.now()
            }

            request_id = int(request_data[2])

            if request_data[1] == 'A':
                userrequest_data = userrequest.UserRequest().get_id(request_id)
                to_user_id = userrequest_data['user']['id']

                data.update({'userrequest': request_id})

                relation_data = userrequest.UserRequest().get_relation(int(request_data[0]))
                product_data = relation_data.get('product')
            elif request_data[1] == 'C':
                paidrequest_data = paidrequest.PaidRequest().get_id(request_id)
                to_user_id = paidrequest_data['user']['id']

                data.update({'paidrequest': request_id})

                relation_data = paidrequest.PaidRequest().get_relation(int(request_data[0]))
                product_data = relation_data.get('product')

            data.update(**{
                'visible': True,
                'has_code': True,
                'content': DEFAULT_REQUEST_MESSAGE.format(product_data.get('title'), gift_link),
                'to_user': to_user_id
            })

            message.Message().push(**data)

            notification_params = data

            notification_params.pop('date')
            notification_params.pop('user')

            notification.Notification().push(
                to_user_id,
                11,
                **notification_params
            )

            if request_data[1] == 'A':
                userrequest.UserRequest().set_sent(
                    int(request_data[0]),
                    gid=gift_link
                )
            elif request_data[1] == 'C':
                paidrequest.PaidRequest().set_sent(
                    int(request_data[0]),
                    gid=gift_link
                )

            mail.read()


if __name__ == '__main__':
    Email(
        config.EMAIL_USERNAME,
        config.EMAIL_PASSWORD
    ).find_gift_emails()
