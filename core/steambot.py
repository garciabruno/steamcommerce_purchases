#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import os
import json
import time
import base64

import steam
import steam.guard
import steam.enums.emsg

import config
from core import logger

log = logger.Logger('steam.bot', 'steam.bot.log').get_logger()


def get_data_from_file(path):
    f = open(os.path.join(os.getcwd(), path), 'r')
    raw = f.read()
    f.close()

    return json.loads(raw)


class SteamBot(object):
    def __init__(self, account_name, password, shared_secret=None):
        log.info(
            u'Initializing SteamBot for account {0}. Use 2FA: {1}'.format(
                account_name,
                'YES' if shared_secret else 'NO'
            )
        )

        self.steamclient = steam.SteamClient()
        self.steamclient.set_credential_location('data')

        self.account_name = account_name
        self.password = password
        self.logged_in = False

        self.shared_secret = shared_secret

        self.friend_add_results = {}
        self.last_messages_received = {}

    def init(self):
        self.steamclient.on('logged_on', self.client_logged_on)
        self.steamclient.on('connected', self.client_connected)
        self.steamclient.on('disconnected', self.client_disconnected)

        self.steamclient.on(
            steam.enums.emsg.EMsg.ClientFriendMsgIncoming,
            self.client_incoming_message
        )

        self.steamclient.friends.on('friend_new', self.client_friend_new)
        self.steamclient.friends.on('friend_invite', self.client_friend_invite)
        self.steamclient.friends.on('friend_removed', self.client_friend_removed)
        self.steamclient.friends.on('friend_add_result', self.client_friend_add_result)

        self.login()
        self.connect()

    def login(self):
        log.info('Logging into account {0}'.format(self.account_name))

        if not self.shared_secret:
            self.steamclient.login(self.account_name, self.password)
        else:
            twofactor_code = self.generate_twofactor_code(self.shared_secret)
            log.info('Received 2FA code {0}'.format(twofactor_code))

            self.steamclient.login(self.account_name, self.password, two_factor_code=twofactor_code)

        self.logged_in = True

    def logout(self):
        log.info(u'Logging out from account {}'.format(self.account_name))

        self.logged_in = False
        self.steamclient.logout()

    def generate_twofactor_code(self, shared_secret):
        return steam.guard.generate_twofactor_code(base64.b64decode(shared_secret))

    def connect(self):
        log.info(u'Connecting to Steam CM servers')

        self.steamclient.connect()

    def close(self):
        log.info(
            u'SteamBot for account {0} is shutting down'.format(
                self.account_name
            )
        )

        self.logout()

    def message_client(self, steamid, message):
        return steam.client.user.SteamUser(steamid, self.steamclient).send_message(message)

    def get_avatar_url(self, steamid):
        return self.steamclient.get_user(steamid).get_avatar_url()

    def get_friends_list(self):
        return filter(lambda x: x.relationship == 3, self.steamclient.friends)

    def add_friend(self, steamid):
        self.steamclient.friends.add(steam.client.user.SteamID(steamid))

    def remove_friend(self, steamid):
        self.steamclient.friends.remove(steam.client.user.SteamID(steamid))

    '''
    Events
    '''

    def client_connected(self):
        log.info(u'A connection was made to the Steam CM servers')

    def client_disconnected(self):
        log.info(u'Disconnected from Steam CM servers')

        if self.logged_in:
            self.connect()  # Attempt re-connection

    def client_logged_on(self):
        log.info(u'Logged on as {}'.format(self.account_name))

    def client_incoming_message(self, proto_msg):
        if proto_msg.body.chat_entry_type != 1:
            # Ignore this EChatEntryType (Typing, InviteGame, etc...)

            return

        from_steam_id = proto_msg.body.steamid_from
        message = proto_msg.body.message.rstrip().strip("\0")

        from_steam_user = self.steamclient.get_user(from_steam_id)
        time_diff = time.time() - (self.last_messages_received.get(from_steam_id) or time.time())

        if time_diff < 1 or time_diff > (2 * 60 * 60):
            self.message_client(from_steam_id, config.AUTO_REPLY_MESSAGE)
            self.last_messages_received[from_steam_id] = time.time()

        log.info(u'{0}: {1}'.format(from_steam_user.name, message.decode('utf-8')))

    def client_friend_new(self, steam_user):
        log.info(u'Accepted a friend invite from {}'.format(steam_user))

        try:
            del self.friend_add_results[steam_user.steam_id.as_64]
        except:
            pass

    def client_friend_removed(self, steam_user):
        log.info(u'{} is no longer in friends list'.format(steam_user))

        try:
            del self.friend_add_results[steam_user.steam_id.as_64]
        except:
            pass

        try:
            del self.friend_add_results['0']
        except:
            pass

    def client_friend_invite(self, steam_user):
        log.info(u'Received a friend invite from {}'.format(steam_user))

        self.add_friend(steam_user.steam_id.as_64)

    def client_friend_add_result(self, result, steam_id):
        log.info(u'Received {0} after adding {1}'.format(repr(result), steam_id))

        self.friend_add_results[steam_id.as_64] = result.value

    def run_forever(self):
        try:
            self.steamclient.run_forever()
        except KeyboardInterrupt:
            self.close()
