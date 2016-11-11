#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import enum


class EBotEnum(enum.IntEnum):
    def __str__(self):
        return str(self.value)


class ECurrencyType(EBotEnum):
    USD = 1
    BRL = 2
    MXN = 3


class EBotType(EBotEnum):
    Standard = 1
    VacGames = 2
    Delivery = 3


class EBotState(EBotEnum):
    StandingBy = 1
    PushingItemsToCart = 2
    PurchasingCart = 3
    WaitingForSufficientFunds = 4
    BlockedForTooManyPurchases = 5


class EBotResult(EBotEnum):
    NotBotAvailableFound = 6
    RaisedUnknownException = 7
    ReachedMaxCartCount = 8
    ReachedMaxCartTimespan = 9
    Succeded = 10


class ECartResult(EBotEnum):
    UnableToRetrieveCartFromCrawler = 10
    UnableToRetrieveCartItemGid = 11
    DidNotFindShoppingCartGid = 12


class EPurchaseResult(EBotEnum):
    GetCartCheckoutFailed = 13
    PostInitTransactionFailed = 14
    TransIdNotFoundInResponse = 15
    GetFinalPriceFailed = 16
    FinalPriceUnsucceded = 17
    PostFinalizeTransactionFailed = 18
    GetTransactionStatusFailed = 19
    Succeded = 20
