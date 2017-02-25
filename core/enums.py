#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from enum import IntEnum


class EWebAccountResult(IntEnum):
    Success = 1
    CrawlerFailed = 2
    Failed = 3
    UnknownException = 4
    ResponseNotSerializable = 5


class ECartResult(IntEnum):
    Added = 1
    Removed = 2
    Failed = 3
    CartNotGifteable = 4
    CartDissapeared = 5
    CartReset = 6


class ETransactionResult(IntEnum):
    Success = 1
    Fail = 2
    ShoppingCartGIDNotFound = 3
    TransIdNotFound = 4
    InsufficientFunds = 5
    TooManyPurchases = 6
