#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import peewee
import config
import enums

if config.USE_SQLITE:
    database = peewee.SqliteDatabase(
        config.DB_PATH, threadlocals=True
    )
else:
    database = peewee.MySQLDatabase(
        config.DB_NAME,
        host=config.DB_HOST,
        user=config.DB_USER,
        passwd=config.DB_PASSWD
    )


class BaseModel(peewee.Model):
    class Meta:
        database = database


class Bot(BaseModel):
    bot_identifier = peewee.IntegerField()
    bot_type = peewee.IntegerField(default=enums.EBotType.Standard)
    name = peewee.CharField()
    bot_currency_type = peewee.IntegerField(enums.ECurrencyType.USD)
    last_cart_push = peewee.DateTimeField(null=True)
    last_cart_purchase = peewee.DateTimeField(null=True)
    last_failed_purchase = peewee.DateTimeField(null=True)
    current_cart_count = peewee.IntegerField(default=0)
    current_state = peewee.IntegerField(default=enums.EBotState.StandingBy)
    account_balance = peewee.CharField(null=True)
    enabled = peewee.BooleanField(default=True)
    steamid = peewee.CharField(null=True)
    avatar_url = peewee.CharField(null=True)
    max_cart_until_purchase = peewee.IntegerField(default=50)
    max_timespan_until_purchase = peewee.IntegerField(default=120)
    data_filename = peewee.CharField(null=True)
    session_filename = peewee.CharField(null=True)
