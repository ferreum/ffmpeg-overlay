#!/usr/bin/python
# File:        plotevents.py
# Description: plotevents
# Created:     2017-06-05

import js
import argparse
import sys
from common import ArgvError


class PlotHandler(js.Handler):

    lasttime = None

    def __init__(self, evs, allstates, adapters):
        js.Handler.__init__(self, evs)
        self.allstates = allstates
        self.origin_to_adapters = origin_to_adapters = {}
        self.recorded_events = ev = {}
        for adapter in adapters:
            ev[adapter] = []
            for o in adapter.origin:
                try:
                    olist = origin_to_adapters[o]
                except KeyError:
                    origin_to_adapters[o] = olist = []
                olist.append(adapter)

    def initevents(self, time):
        for adapter, events in self.recorded_events.items():
            events.append((time, adapter(self.allstates)))

    def handle_event(self, event):
        type = event.type & ~js.TY_INIT_BIT
        num = event.number
        spec = (type, num)
        time = event.time
        self.lasttime = time
        for adapter in self.origin_to_adapters.get(spec, ()):
            events = self.recorded_events[adapter]
            if events:
                prevevent = events[-1]
                if prevevent[0] < time - 10:
                    events.append((time - 10, prevevent[1]))
            events.append((time, adapter(self.allstates)))


COLORS = {
    'A': '#3dba41',
    'B': '#ff5353',
    'X': '#535fff',
    'Y': '#ffc653',
    'BACK': '#00c2ca',
    'START': '#ca0098',
    'GUIDE': '#cfaeff',
    'RB': '#30ff30',
    'LB': '#3030ff',
    'RT': '#ff3030',
    'LT': '#ff880a',
    'STL_X': '#5b5b99',
    'STL_Y': '#5b5b99',
    'STR_X': '#995b5b',
    'STR_Y': '#995b5b',
}

PLOT_IDS = {
    'RB': 3,
    'LB': 3,
    'STL_X': 2,
    'STL_Y': 2,
    'STR_X': 2,
    'STR_Y': 2,
    'RT': 3,
    'LT': 3,
}


def convert_timearg(s, default=None):
    if s is not None:
        return int(float(s) * 1000)
    else:
        return default


def main(argv):
    progname = argv.pop(0).rpartition('/')[2]
    parser = argparse.ArgumentParser(prog=progname)
    parser.add_argument('-d', '--delay', default=None, help="Additional start delay in seconds")
    parser.add_argument('-s', '-ss', '--start', default=None, help="Start time in seconds (opposite of --delay)")
    parser.add_argument('-S', '--absolute-start', default=None, help="Absolute start time (additional to -s)")
    parser.add_argument('-T', '--type', default='xboxdrv', help="Specify the controller type to use")
    parser.add_argument('-i', '--inputs', nargs='*',
                        default=['STL_X', 'STL_Y', 'STR_X', 'STR_Y', 'LT', 'RT', 'LB', 'RB', 'BACK', 'START', 'GUIDE', 'A', 'B', 'X', 'Y'],
                        help="Specify controller inputs to plot")
    endgroup = parser.add_mutually_exclusive_group()
    endgroup.add_argument('-to', '--until', default=None, help="End time in seconds after --delay")
    endgroup.add_argument('-t', '--duration', default=None, help="Duration in seconds after the actual start time")
    args = parser.parse_args(argv)

    args.start = convert_timearg(args.start, 0)
    if args.absolute_start is not None:
        args.absstart = int(args.absolute_start)
    else:
        args.absstart = 0
    args.delay = convert_timearg(args.delay, 0)
    args.until = convert_timearg(args.until, None)
    args.duration = convert_timearg(args.duration, None)

    import overlayapi as api
    api.import_all_config()

    try:
        ctype = api.CONTROLLER_TYPES[args.type]()
    except KeyError:
        raise ArgvError("no such controller type: %r" % (args.type,), parser)

    adapters = [api.to_adapter(getattr(ctype, name)) for name in args.inputs]

    evs = js.HandlerJsEvents(sys.stdin)

    allstates = js.AllstatesHandler(evs)
    allstates.attach()
    plotter = PlotHandler(evs, allstates, adapters)

    evs.work_all(until=args.absstart)
    firsttime = evs.pending_event.time
    # ensure we processed all init events
    evs.work_all(until=firsttime)
    # read until we reach our start time
    starttime = firsttime + args.start - args.delay
    evs.work_all(until=starttime)

    plotter.initevents(starttime)
    plotter.attach()
    evs.work_all()

    import matplotlib.pyplot as plt
    import numpy as np

    plotnums = set()
    for name in args.inputs:
        plotnums.add(PLOT_IDS.get(name, 1))
    plotmap = {num: i for i, num in enumerate(sorted(list(plotnums)), 1)}

    firstplot = None
    plots = {}
    for num, i in plotmap.items():
        plot = plt.subplot(len(plotmap), 1, i, sharex=firstplot,
                         xlabel='time (seconds)', ylabel="value")
        if firstplot is None:
            firstplot = plot
        plots[num] = plot

    def plotevents(events, plot, *args, **kw):
        e = np.array(events)
        times = (e[:,0] - starttime) * .001
        values = e[:,1]
        plot.fill_between(times, values, 0,
                        where=values>.01, alpha=0.5, **kw)

    for name, adapter in zip(args.inputs, adapters):
        plot = plots[PLOT_IDS.get(name, 1)]

        events = plotter.recorded_events[adapter]
        color = COLORS.get(name, '#000000')
        plotevents(events, plot, color=color, label=name)

    if plotter.lasttime is None:
        print("no events")
    else:
        end = plotter.lasttime - starttime
        end *= .001
        for plot in plots.values():
            plot.vlines([end], 0, 1, '#000000',
                      label='end', linewidth=1, linestyle='-.')

    for plot in plots.values():
        plot.legend()

    plt.show()

    return 0


if __name__ == '__main__':
    from common import run_main
    run_main(main)

# vim:set sw=4 ts=8 sts=4 et sr ft=python fdm=marker tw=0:
