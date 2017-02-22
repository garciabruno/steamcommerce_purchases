#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import os
import sys
import logging


class Logger(object):
    def __init__(self, name, log_name):
        self.name = name
        self.log_name = log_name

    def get_logger(self, debug=False, stdout=True, fdout=True):
        log = logging.getLogger(self.name)
        log.propagate = False
        log.handlers = []

        if debug:
            log.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)

        format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        if stdout:
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(format)
            log.addHandler(ch)

        if fdout:
            fh = logging.FileHandler(
                os.path.join(os.getcwd(), 'logs/{0}'.format(self.log_name))
            )

            fh.setFormatter(format)
            log.addHandler(fh)

        return log
