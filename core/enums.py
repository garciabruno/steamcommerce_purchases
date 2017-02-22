#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from enum import IntEnum


class EWebAccountResult(IntEnum):
    CrawlerFailed = 0
    Success = 1
    Failed = 2
    UnknownException = 3


class ECartResult(IntEnum):
    Added = 1
    Removed = 2
    Failed = 3
    CartNotGifteable = 4
    CartDissapeared = 5
