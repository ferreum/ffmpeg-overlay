#!/usr/bin/python

# This is not a javascript module.

import sys
import re
import contextlib


TY_BUTTON = 1
TY_AXIS = 2
TY_INIT_BIT = 0x80


class Event(object):

    def __init__(self, ty, fields, text=None):
        self.ty = ty
        self.fields = fields
        self.text = text

    def __getattr__(self, name):
        try:
            return int(self.fields[name])
        except KeyError:
            raise AttributeError("Key not found in %r" % (self,))

    def is_type(self, ty):
        return (self.type & ~TY_INIT_BIT) == ty

    def __repr__(self):
        return ("<Event: " + self.ty + ": "
                + ", ".join((k + "=" + v for k, v in self.fields.items()))
                + ">")


def make_event(line):
    ty, sep, tail = line.partition(":")
    splits = re.split(r", *", tail.strip())
    fields = {}
    for f in splits:
        n, sep, v = f.partition(" ")
        if sep:
            fields[n] = v
    return Event(ty, fields, text=line)


class LineConvertingReader(object):

    """Provide a readline method that decodes lines from utf-8 transparently.

    Cannot use codecs.getreader('utf-8')(reader) because it adds buffering. """

    def __init__(self, reader):
        self.reader = reader
        try:
            self.fileno = reader.fileno
        except AttributeError:
            pass

    def readline(self):
        return self.reader.readline().decode('utf-8')


class JsEvents(object):

    def __init__(self, stream):
        self.stream = stream
        self.running = True
        self.exit_status = 0
        self.pending_event = None
        self.previous_event = None

    def parse_jstest_event(self, line):
        if not re.match(r"\w+:", line):
            return None
        else:
            return make_event(line)

    def ignored_line(self, line):
        pass

    def _next_event(self):
        while True:
            line = self.stream.readline()
            if line == "":
                return None
            line = line.rstrip('\n')
            event = self.parse_jstest_event(line)
            if event is not None:
                return event
            self.ignored_line(line)

    def work(self):
        event = self._next_event()
        if event is None:
            self.running = False
            return False
        self.handle_event(event)
        return self.running

    def work_all(self, until=None):
        event = self.pending_event
        if event is None:
            event = self._next_event()
        else:
            self.pending_event = None
        while True:
            if event is None:
                self.running = False
                return False
            if until is not None:
                if until == 'initialized':
                    if (event.type & TY_INIT_BIT) == 0:
                        self.pending_event = event
                        return True
                elif event.time > until:
                    self.pending_event = event
                    return True
            self.previous_event = event
            self.handle_event(event)
            if not self.running:
                return False
            event = self._next_event()

    def exit(self):
        self.running = False

    def handle_event(self, event):
        print(repr(event))


class Handler(object):

    def __init__(self, events):
        if not isinstance(events, HandlerJsEvents):
            raise TypeError
        self.events = events

    def attach(self):
        self.events.h_add(self)

    def remove(self):
        self.events.h_remove(self)

    def handle_event(self, event):
        pass

    def handle_unknown(self, line):
        pass


class HandlerJsEvents(JsEvents):

    def __init__(self, stream):
        JsEvents.__init__(self, stream)
        self.handling = False
        self.handlers = []
        self.removed = []
        self.added = []

    def h_add(self, handler):
        if self.handling:
            if handler in self.added:
                raise ValueError(repr(handler) + " is already adding")
            if handler in self.removed:
                raise ValueError(repr(handler) + " is removing")
            if handler in self.handlers:
                raise ValueError(repr(handler) + " is added")
            self.added.append(handler)
        else:
            self.handlers.append(handler)

    def h_remove(self, handler):
        if self.handling:
            if handler in self.added:
                raise ValueError(repr(handler) + " is adding")
            if handler in self.removed:
                raise ValueError(repr(handler) + " is already removing")
            if handler not in self.handlers:
                raise ValueError(repr(handler) + " is not added")
            self.removed.append(handler)
        else:
            self.handlers.remove(handler)

    @contextlib.contextmanager
    def _handling(self):
        self.handling = True
        yield
        for h in self.removed:
            self.handlers.remove(h)
        for h in self.added:
            self.handlers.append(h)
        self.added.clear()
        self.removed.clear()
        self.handling = False


    def handle_event(self, event):
        with self._handling():
            for h in self.handlers:
                h.handle_event(event)

    def ignored_line(self, line):
        with self._handling():
            for h in self.handlers:
                h.handle_unknown(line)


class AllstatesHandler(Handler):

    def __init__(self, events):
        Handler.__init__(self, events)
        self.states = {}

    def log(self):
        msg = ""
        for (t, n), v in sorted(self.states.items()):
            msg += "(%d,%d):%d " % (t, n, v)
        print(msg[:-1] if msg else "")

    def handle_event(self, event):
        if event.ty == "Event":
            t = event.type & ~TY_INIT_BIT
            n = event.number
            self.states[(t, n)] = event.value


def start_jstest(device):
    import subprocess as sp
    return sp.Popen(["stdbuf", "-oL", "jstest", "--event", device],
                    stdout=sp.PIPE)


def main(args):
    if len(args) < 1:
        device = "/dev/input/js1"
    else:
        device = args[0]
    proc = start_jstest(device)
    evs = JsEvents(LineConvertingReader(proc.stdout))
    evs.work_all()
    return evs.exit_status


if __name__ == '__main__':
    exit(main(sys.argv[1:]))

# vim:set sw=4 ts=8 sts=4 et sr ft=python fdm=marker tw=0:
