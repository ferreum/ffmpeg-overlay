#!/usr/bin/python
# File:        live.py
# Description: live
# Created:     2017-07-16


import re
from contextlib import suppress
import asyncio
from gi.repository import Gtk
import cairo

import js


class JsWidget(Gtk.DrawingArea):

    enabled = False

    def __init__(self, layout, anim, scale=15.0):
        Gtk.DrawingArea.__init__(self)

        self.layout = layout
        self.anim = anim

        self.set_size_request(layout.width * scale, layout.height * scale)
        self.connect('draw', self.__on_draw)

    def enable(self):
        self.enabled = True

    def __on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        if self.enabled:
            anim = self.anim
            width = widget.get_allocated_width()
            height = widget.get_allocated_height()
            layout = self.layout
            scale_x = width / layout.width
            scale_y = height / layout.height
            scale = min(scale_x, scale_y)
            anim.update()
            cr.save()
            try:
                cr.scale(scale, scale)
                anim.draw(cr)
            finally:
                cr.restore()
            if anim.context.needs_update:
                anim.context.needs_update = False
                self.queue_draw()


class LiveWorker(object):

    def __init__(self, device_path, evs):
        self.device_path = device_path
        self.evs = evs

    async def do_work(self):
        evs = self.evs
        process = await asyncio.create_subprocess_exec(
            "stdbuf", "-o0", "jstest", "--event", self.device_path,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE)
        try:
            event = None
            num_init_events = None
            evnum = 0
            lines = process.stdout.__aiter__()
            async for line in lines:
                line = line.decode('utf-8')
                match = re.search(r"has (\d+) axes and (\d+) buttons\.", line)
                if match:
                    num_init_events = int(match.group(1)) + int(match.group(2))
                event = evs.feed(line)
                if event:
                    evnum += 1
                if num_init_events and evnum >= num_init_events:
                    break
                if event is not None and (event.type & js.TY_INIT_BIT) == 0:
                    break
            self.on_init()
            async for line in lines:
                evs.feed(line.decode('utf-8'))
                self.on_event()
                evnum += 1
        finally:
            with suppress(ProcessLookupError):
                process.terminate()

    def on_init(self):
        pass

    def on_event(self):
        pass


# vim:set sw=4 ts=8 sts=4 et sr ft=python fdm=marker tw=0:
