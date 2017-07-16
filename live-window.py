#!/usr/bin/python
# File:        live-window.py
# Description: live-window
# Created:     2017-07-16


import argparse
import asyncio
from contextlib import suppress

import js
from common import ArgvError


def main(argv):
    progname = argv.pop(0).rpartition('/')[2]
    parser = argparse.ArgumentParser(prog=progname)
    parser.add_argument("DEVICE", help="The joystick device name.")
    parser.add_argument('-t', '--type', default='auto',
                        help="Specify the controller type to use")
    parser.add_argument('-l', '--layout', default='distance',
                        help="Name of the layout to use")
    parser.add_argument('-T', '--theme', default='default',
                        help="Specify the theme to use")
    args = parser.parse_args(argv)

    import overlayapi as api
    api.import_all_config()

    try:
        ctype = api.CONTROLLER_TYPES[args.type]()
    except KeyError:
        raise ArgvError("no such controller type: %r" % (args.type,), parser)
    try:
        layoutcls = api.LAYOUTS[args.layout]
    except KeyError:
        raise ArgvError("no such layout: %r" % (args.layout,), parser)
    try:
        theme = api.THEMES[args.theme]()
    except KeyError:
        raise ArgvError("no such theme: %s" % (args.theme,), parser)

    import gi
    gi.require_version('Gtk', '3.0')
    import gbulb
    import gbulb.gtk
    from gi.repository import Gtk
    from live import JsWidget, LiveWorker

    asyncio.set_event_loop_policy(gbulb.gtk.GtkEventLoopPolicy())
    gbulb.install(gtk=True)
    loop = asyncio.get_event_loop()

    layout = layoutcls(ctype)
    evs = js.HandlerJsEvents()
    context = api.Context(theme, ctype, evs)

    anim = api.LiveControlsAnimation(context, layout.controls)
    anim.init()
    jswidget = JsWidget(layout, anim)

    win = Gtk.Window()
    win.connect("delete-event", lambda *args: task.cancel())
    win.set_property('decorated', False)
    screen = win.get_screen()
    argb = screen.get_rgba_visual()
    if argb:
        win.set_visual(argb)
    win.add(jswidget)
    win.show_all()

    worker = LiveWorker(args.DEVICE, evs)
    worker.on_init = lambda: jswidget.enable()
    worker.on_event = lambda: jswidget.queue_draw()
    task = asyncio.ensure_future(worker.do_work())

    with suppress(asyncio.CancelledError):
        loop.run_until_complete(task)


if __name__ == '__main__':
    from common import run_main
    run_main(main)


# vim:set sw=4 ts=8 sts=4 et sr ft=python fdm=marker tw=0:
