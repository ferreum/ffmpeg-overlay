#!/usr/bin/python
# File:        common.py
# Description: common
# Created:     2017-06-05

class ArgvError(Exception):

    def __init__(self, msg, parser):
        Exception.__init__(self, msg)
        self.parser = parser


def run_main(main):
    import sys
    try:
        exit(main(sys.argv))
    except KeyboardInterrupt:
        exit(127)
    except ArgvError as e:
        e.parser.error(e)


# vim:set sw=4 ts=8 sts=4 et sr ft=python fdm=marker tw=0:
