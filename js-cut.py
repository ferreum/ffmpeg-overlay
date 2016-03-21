#!/usr/bin/python

import js
import argparse
import sys


def print_event(ty, type, time, num, value):
    print("%s: type %d, time %d, number %d, value %d" % (ty, type, time, num, value))


class PrintHandler(js.Handler):

    def handle_event(self, event):
        if event.type & js.TY_INIT_BIT:
            raise Exception("init event in print handler")
        print(event.text)


def convert_timearg(s, default=None):
    if s is not None:
        return int(float(s) * 1000)
    else:
        return default


def print_start(allstates, starttime):
    for k, v in allstates.states.items():
        type, num = k
        type = type | js.TY_INIT_BIT
        print_event("Event", type, starttime, num, v)


def main(argv):
    progname = argv.pop(0).rpartition('/')[2]

    parser = argparse.ArgumentParser(prog=progname)
    parser.add_argument('-d', '--delay', default=None, help="Additional start delay in seconds")
    parser.add_argument('-s', '-ss', '--start', default=None, help="Start time in seconds (opposite of --delay)")
    endgroup = parser.add_mutually_exclusive_group()
    endgroup.add_argument('-to', '--until', default=None, help="End time in seconds after --delay")
    endgroup.add_argument('-t', '--duration', default=None, help="Duration in seconds after the actual start time")
    args = parser.parse_args(argv)

    args.start = convert_timearg(args.start, 0)
    args.delay = convert_timearg(args.delay, 0)
    args.until = convert_timearg(args.until, None)
    args.duration = convert_timearg(args.duration, None)

    evs = js.HandlerJsEvents(sys.stdin)
    allstates = js.AllstatesHandler(evs)
    allstates.attach()
    evs.ignored_line = print

    print("jsevents modified with js-cut.py")
    evs.work_all(until=0)
    firsttime = evs.pending_event.time
    # ensure we processed all init events
    evs.work_all(until=firsttime)
    # read until we reach our start time
    starttime = firsttime + args.start - args.delay
    evs.work_all(until=starttime)
    print_start(allstates, starttime)
    allstates.remove()

    endtime = None
    if args.until is not None:
        endtime = firsttime + args.until - args.delay
    elif args.duration is not None:
        endtime = firsttime + args.duration + args.start - args.delay
    PrintHandler(evs).attach()
    evs.work_all(until=endtime)


if __name__ == '__main__':
    exit(main(sys.argv))


# vim:set sw=4 ts=8 sts=4 et sr ft=python fdm=marker tw=0:
