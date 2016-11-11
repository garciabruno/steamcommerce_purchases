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
    ''' Responses '''

    CouldNotJSONResponse = 13
    ResponseDidNotContainSuccess = 14
    ResponseDidNotContainTransId = 15
    NotEnoughBalance = 16

    ''' Requests '''

    GetCartCheckoutFailed = 17
    PostInitTransactionFailed = 18
    GetFinalPriceFailed = 19
    FinalPriceUnsucceded = 20
    PostFinalizeTransactionFailed = 21
    GetTransactionStatusFailed = 22
    Succeded = 23

    ''' Other '''

    RaisedUnknownException = 24
