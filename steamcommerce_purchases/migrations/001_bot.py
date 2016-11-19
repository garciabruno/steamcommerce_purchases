#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import logging
import peewee
from playhouse.migrate import *

from steamcommerce_purchases import config

logging.basicConfig(
    format='%(asctime)s %(message)s',
    level=logging.DEBUG
)

if config.USE_SQLITE:
    database = peewee.SqliteDatabase(config.DB_PATH, threadlocals=True)
    migrator = SqliteMigrator(database)
else:
    database = peewee.MySQLDatabase(
        config.DB_NAME,
        host=config.DB_HOST,
        user=config.DB_USER,
        passwd=config.DB_PASSWD
    )
    migrator = MySQLMigrator(database)


logging.debug('Begining migration')

last_shopping_cart_purchase = peewee.CharField(null=True)

migrate(
    migrator.add_column(
        'bot',
        'last_shopping_cart_purchase',
        last_shopping_cart_purchase
    )
)
