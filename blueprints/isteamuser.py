#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from workers import WORKERS

from flask import request
from flask import jsonify
from flask import redirect
from flask import url_for
from flask import Blueprint

isteamuser = Blueprint('isteamuser', __name__)


@isteamuser.route('/SendMessage/')
def GetProductInfo():
    user = request.args.get('user', '')
    message = request.args.get('message', '')
    network_id = request.args.get('network_id', '')

    if not user or not message or not network_id:
        return jsonify({})

    steambot = WORKERS[network_id]

    return jsonify(steambot.message_client(int(user), message) or request.args)


@isteamuser.route('/AddFriend/')
def AddFriend():
    steam_id = request.args.get('steam_id', '')
    network_id = request.args.get('network_id', '')

    if not steam_id or not network_id:
        return jsonify({'error': 'steam_id or network_id are missing'})

    steambot = WORKERS[network_id]
    steambot.add_friend(int(steam_id))

    return redirect(url_for('isteamuser.GetFriendAddResults', network_id=network_id))


@isteamuser.route('/GetFriendAddResults/')
def GetFriendAddResults():
    network_id = request.args.get('network_id', '')

    if not network_id:
        return jsonify({'error': 'network_id is missing'})

    steambot = WORKERS[network_id]

    return jsonify(steambot.friend_add_results)


@isteamuser.route('/GetFriendsList/')
def GetFriendsList():
    network_id = request.args.get('network_id', '')
    ids = request.args.get('ids', '')

    if not network_id:
        return jsonify({'error': 'No network_id provided'})

    result = []
    friendslist = WORKERS[network_id].get_friends_list()

    if ids:
        return jsonify([x.steam_id.as_64 for x in friendslist])

    for friend in friendslist:
        result.append({
            'SteamID64': friend.steam_id.as_64,
            'avatar_url': friend.get_avatar_url(),
            'name': friend.name
        })

    return jsonify(result)
