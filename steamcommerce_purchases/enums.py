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
    BlockedForUnknownReason = 6


class EBotResult(EBotEnum):
    NotBotAvailableFound = 7
    RaisedUnknownException = 8
    ReachedMaxCartCount = 9
    ReachedMaxCartTimespan = 10
    Succeded = 11


class ECartResult(EBotEnum):
    UnableToRetrieveCartFromCrawler = 11
    UnableToRetrieveCartItemGid = 12
    DidNotFindShoppingCartGid = 13


class EPurchaseResult(EBotEnum):
    ''' Responses '''

    CouldNotJSONResponse = 14
    ResponseDidNotContainSuccess = 15
    ResponseDidNotContainTransId = 16
    InsufficientFunds = 17

    ''' Requests '''

    GetCartCheckoutFailed = 18
    PostInitTransactionFailed = 19
    GetFinalPriceFailed = 20
    FinalPriceUnsucceded = 21
    PostFinalizeTransactionFailed = 22
    GetTransactionStatusFailed = 23
    Succeded = 24

    ''' Other '''

    RaisedUnknownException = 25
    ReachedMaximumPollAttemps = 26


class ECommitLevel(EBotEnum):
    Uncommited = 0
    AddedToCart = 1
    Purchased = 2
    FailedToAddToCart = 3
