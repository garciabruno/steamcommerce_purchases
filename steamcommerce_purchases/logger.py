#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import sys
import logging


class Logger(object):
    def __init__(self, name, log_name):
        self.name = name
        self.log_name = log_name

    def get_logger(self, debug=True, stdout=True, fdout=True):
        log = logging.getLogger(self.name)

        if debug:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)

        format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        if stdout:
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(format)
            log.addHandler(ch)

        if fdout:
            fh = logging.FileHandler(
                'logs/{0}'.format(self.log_name)
            )

            fh.setFormatter(format)
            log.addHandler(fh)

        return log
