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
    UnableToRetrieveCartFromCrawler = 12
    UnableToRetrieveCartItemGid = 13
    DidNotFindShoppingCartGid = 14


class EPurchaseResult(EBotEnum):
    ''' Responses '''

    CouldNotJSONResponse = 15
    ResponseDidNotContainSuccess = 16
    ResponseDidNotContainTransId = 17
    InsufficientFunds = 18

    ''' Requests '''

    GetCartCheckoutFailed = 19
    PostInitTransactionFailed = 20
    GetFinalPriceFailed = 21
    FinalPriceUnsucceded = 22
    PostFinalizeTransactionFailed = 23
    GetTransactionStatusFailed = 24
    Succeded = 25

    ''' Other '''

    RaisedUnknownException = 26
    ReachedMaximumPollAttemps = 27


class ECommitLevel(EBotEnum):
    Uncommited = 0
    AddedToCart = 1
    Purchased = 2
    FailedToAddToCart = 3
