#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import datetime

import enums
import models


class BotController(object):
    def __init__(self):
        self.model = models.Bot

    def create(self, *args, **kwargs):
        model = self.model(*args, **kwargs)
        commited = model.save()

        if not commited:
            raise Exception(
                'Could not create new row on a table'
            )

        return model.id

    def update(self, *args, **kwargs):
        if not 'id' in kwargs.keys():
            raise Exception('Called updated without id')

        obj = self.model.get(id=kwargs['id'])

        update_kwargs = kwargs.copy()
        update_kwargs.pop('id')

        for update_key in update_kwargs.keys():
            setattr(obj, update_key, update_kwargs[update_key])

        commited = obj.save()

        if not commited:
            raise Exception(
                'Could not update row on table'
            )

        return commited

    def get_bots(self):
        return self.model.select().where(self.model.enabled == True)

    def get_first_active_bot(self):
        try:
            return self.model.get(
                enabled=True,
                current_state=enums.EBotState.StandingBy
            )
        except self.model.DoesNotExist:
            return enums.EBotResult.NotBotAvailableFound
        except Exception:
            return enums.EBotResult.RaisedUnknownException

    def get_bot_id(self, bot_id):
        try:
            return self.model.get(
                id=bot_id,
                current_state=enums.EBotState.StandingBy
            )
        except self.model.DoesNotExist:
            return enums.EBotResult.NotBotAvailableFound
        except Exception:
            return enums.EBotResult.RaisedUnknownException

    def set_last_cart_push(self, bot_id):
        return self.update(**{
            'id': bot_id,
            'last_cart_push': datetime.datetime.now()
        })

    def set_last_cart_purchase(self, bot_id, shopping_cart_gid):
        return self.update(**{
            'id': bot_id,
            'last_cart_purchase': datetime.datetime.now(),
            'last_shopping_cart_purchase': shopping_cart_gid
        })

    def set_last_failed_cart_purchase(self, bot_id):
        return self.update(**{
            'id': bot_id,
            'last_failed_purchase': datetime.datetime.now()
        })

    def set_bot_state(self, bot_id, state):
        params = {'id': bot_id, 'current_state': state}

        return self.update(**params)
