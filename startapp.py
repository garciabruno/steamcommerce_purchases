#! /usr/bin/env python
# -*- coding:Utf-8 -*-

import config


if __name__ == "__main__":
    import sys
    sys.path.insert(0, '..')
    __import__('app').app.run(
        debug=config.DEBUG,
        host=config.HOST,
        threaded=True
    )
else:
    raise RuntimeError('%s not meant for import' % __name__)
