#!/usr/bin/python

import math
import cairocffi as cairo


def snap_rect(cctx, x, y, w, h):
    x, y = cctx.user_to_device(x, y)
    w, h = cctx.user_to_device_distance(w, h)
    return (*cctx.device_to_user(round(x), round(y)),
            *cctx.device_to_user_distance(round(w), round(h)))

def snap_circle(cctx, x, y, r):
    x, y = cctx.user_to_device(x, y)
    r = round(cctx.user_to_device_distance(r, r)[0])
    return (*cctx.device_to_user(round(x), round(y)),
            cctx.device_to_user_distance(r, r)[0])

def snap_point(cctx, x, y, addx=0, addy=0):
    x, y = cctx.user_to_device(x, y)
    return cctx.device_to_user(round(x) + addx, round(y) + addy)

def snap_dist(cctx, d, add=0):
    x, y = cctx.user_to_device_distance(d, 0)
    return cctx.device_to_user_distance(round(x) + add, round(y))[0]


class Look(object):

    def __init__(self, center, hidetime=None, maxoutstyle='none', label=None, labelargs=None):
        self.center = center
        self.label = label
        self.maxoutstyle = maxoutstyle
        self.hidetime = hidetime
        self.last_active = -100000000
        self.alpha = 1.0
        if labelargs is None:
            labelargs = {}
        labelargs.setdefault('size', .88)
        self.labelargs = labelargs

    def init_theme(self, theme):
        if self.hidetime is not None:
            self.alpha = 0.0
        self.textcolor = theme.textcolor

    def update(self, context, value):
        if value > 1.0:
            value = 1.0
        elif value < 0:
            value = 0
        self.value = value
        hidetime = self.hidetime
        if hidetime is not None:
            if value > 0.2:
                self.last_active = context.time
                alpha = 1.0
            elif self.last_active + hidetime > context.time:
                alpha = 1.0 - (context.time - self.last_active) / hidetime
            else:
                alpha = 0.0
            self.alpha = alpha
        return value

    def draw(self, cctx):
        if self.alpha > 0.001:
            self.on_draw(cctx)

    def on_draw(self, cctx):
        label = self.label
        if label is not None:
            cctx.select_font_face(weight=cairo.FONT_WEIGHT_BOLD)
            cctx.set_source_rgba(*self.textcolor, self.alpha)
            cctx.set_font_size(self.labelargs['size'])
            cx, cy = self.center
            # use fixed text for height calculation to align all texts
            # regardless of glyph height
            _, ty, _, th, _, dy = cctx.text_extents("J")
            tx, _, tw, _, dx, _ = cctx.text_extents(self.label)
            cctx.move_to(cx - tw / 2 - tx, cy + ty / 2 - ty)
            cctx.show_text(self.label)

class BgFgLook(Look):

    def __init__(self, center, bgsize=.8, fgsize=1.0, **kwargs):
        Look.__init__(self, center, **kwargs)
        self.bgsize = bgsize
        self.fgsize = fgsize
        self.bgalpha = .5
        self.fgalpha = 1.0

    def init_theme(self, theme):
        Look.init_theme(self, theme)
        self.theme = theme
        self.fgcolor = theme.fgcolor
        self.bgcolor = theme.bgcolor

    def maxout(self, value):
        if value >= 0.98:
            style = self.maxoutstyle
            if style == 'face':
                self.fgcolor = self.theme.maxedcolor
            elif style == 'none':
                pass
            else:
                raise TypeError("invalid maxoutstyle: %r" % (style,))
        else:
            self.fgcolor = self.theme.fgcolor

    def update(self, context, value):
        value = Look.update(self, context, value)
        self.maxout(value)
        return value

class RectLook(BgFgLook):

    def __init__(self, center, size, fancy=True, **kwargs):
        BgFgLook.__init__(self, center, **kwargs)
        self.size = size
        self.fancy = fancy
        bw = size[0] * self.bgsize
        bh = size[1] * self.bgsize
        self.bgbounds = (center[0] - bw * .5, center[1] - bh * .5, bw, bh)

    def on_draw(self, cctx):
        cctx.set_source_rgba(*self.bgcolor, self.bgalpha * self.alpha)
        bx, by, bw, bh = snap_rect(cctx, *self.bgbounds)
        cctx.rectangle(bx, by, bw, bh)
        cctx.fill()
        sw, sh = self.size
        ev = self.value * self.fgsize
        h = sh * ev
        cctx.set_source_rgba(*self.fgcolor, self.fgalpha * self.alpha)
        if self.fancy and ev < self.bgsize:
            cctx.rectangle(*snap_rect(cctx, bx, by + bh - h, bw, h))
        else:
            w = sw * ev
            cx = bx + bw * .5
            cy = by + bh * .5
            cx, cy, w, h = snap_rect(cctx, cx, cy, w / 2, h / 2)
            cctx.rectangle(cx - w, cy - h, w * 2, h * 2)
        cctx.fill()
        BgFgLook.on_draw(self, cctx)

class CircleLook(BgFgLook):

    def __init__(self, center, radius, **kwargs):
        BgFgLook.__init__(self, center, **kwargs)
        self.radius = radius
        self.bg = (*center, radius * self.bgsize)
        self.fg = (*center, radius * self.fgsize)

    def update(self, context, value):
        value = BgFgLook.update(self, context, value)
        self.fg = (*self.center, self.radius * self.fgsize * value)
        return value

    def on_draw(self, cctx):
        cctx.set_source_rgba(*self.bgcolor, self.bgalpha * self.alpha)
        cctx.arc(*snap_circle(cctx, *self.bg), 0, math.pi * 2)
        cctx.fill()
        cctx.set_source_rgba(*self.fgcolor, self.fgalpha * self.alpha)
        cctx.arc(*snap_circle(cctx, *self.fg), 0, math.pi * 2)
        cctx.fill()
        BgFgLook.on_draw(self, cctx)

class StickLook(CircleLook):

    def __init__(self, center, radius, bgsize=.8, fgsize=.55, **kwargs):
        CircleLook.__init__(self, center, radius, bgsize=bgsize, fgsize=fgsize, **kwargs)

    def update(self, context, value):
        vx, vy, vb = value
        mag = math.hypot(vx, vy)
        if mag > 1.0:
            vx /= mag
            vy /= mag
            mag = 1.0
        CircleLook.update(self, context, mag)
        space = self.radius * (1.0 - self.fgsize)
        cx, cy = self.center
        cx = cx + space * vx
        cy = cy + space * vy
        self.fg = (cx, cy, self.radius * self.fgsize)
        return (vx, vy)

class DpadButtonLook(BgFgLook):

    def __init__(self, size, angle, margin=0.0, **kwargs):
        BgFgLook.__init__(self, (size / 2, 0), **kwargs)
        self.size = size
        self.margin = margin
        self.angle = angle

    def on_draw(self, cctx):
        size = self.size
        margin = size * self.margin
        cx = size / 2

        def shape_bounds(w):
            l = snap_dist(cctx, cx - w * .5 + margin, add=-.5)
            r = snap_dist(cctx, cx + w * .5)
            h = snap_dist(cctx, w * .25)
            return l, r, h

        def draw_shape(l, r, h):
            cctx.move_to(r, h)
            cctx.line_to(l + h, h)
            cctx.line_to(l, 0)
            cctx.line_to(l + h, -h)
            cctx.line_to(r, -h)

        bg = shape_bounds(size * self.bgsize)
        fg = shape_bounds(size * self.fgsize)
        _, ar, ah = shape_bounds(size * self.bgsize * .8)

        with cctx:
            cctx.rotate(self.angle)
            cctx.set_source_rgba(*self.bgcolor, self.bgalpha * self.alpha)
            draw_shape(*bg)
            cctx.fill()
            if self.value > .1:
                cctx.set_source_rgba(*self.fgcolor, self.fgalpha * self.alpha)
                draw_shape(*fg)
                cctx.fill()
            cctx.set_source_rgba(*self.textcolor, self.alpha)
            cctx.move_to(ar, 0)
            cctx.line_to(ar - ah, ah)
            cctx.line_to(ar - ah, -ah)
            cctx.fill()
        BgFgLook.on_draw(self, cctx)

class DpadGroupLook(Look):

    def __init__(self, center, radius, fgsize=1., bgsize=.8,
                 margin=.05, hidetime=None, **kwargs):
        Look.__init__(self, center, hidetime=hidetime, **kwargs)
        opts = {'fgsize': fgsize, 'bgsize': bgsize, 'margin': margin}
        self.buttons = [
            DpadButtonLook(radius, 0.0, **opts),
            DpadButtonLook(radius, math.pi * .5, **opts),
            DpadButtonLook(radius, math.pi, **opts),
            DpadButtonLook(radius, math.pi * 1.5, **opts),
        ]

    def init_theme(self, theme):
        Look.init_theme(self, theme)
        for btn in self.buttons:
            btn.init_theme(theme)

    def update(self, context, value):
        def fix_value(value):
            if value >= .1:
                return 1.0
            elif value <= -.1:
                return -1.0
            else:
                return 0
        vx, vy = value
        vx = fix_value(vx)
        vy = fix_value(vy)
        buttons = self.buttons
        buttons[0].update(context, 1.0 if vx > 0.0 else 0.0)
        buttons[1].update(context, 1.0 if vy > 0.0 else 0.0)
        buttons[2].update(context, 1.0 if vx < 0.0 else 0.0)
        buttons[3].update(context, 1.0 if vy < 0.0 else 0.0)
        Look.update(self, context, 1.0 if vx or vy else 0.0)
        for b in buttons:
            b.alpha = self.alpha

    def on_draw(self, cctx):
        with cctx:
            cctx.translate(*snap_point(cctx, *self.center))
            for btn in self.buttons:
                btn.draw(cctx)
        Look.on_draw(self, cctx)


class SimpleStateAdapter(object):

    def __init__(self, spec):
        self.spec = spec

    def __call__(self, allstates):
        return allstates.states[self.spec]

class TimeAdapter(object):

    def __init__(self, duration):
        self.duration = int(duration * 1000)

    def __call__(self, context):
        return min(1.0, context.time / self.duration)

class GroupAdapter(object):

    def __init__(self, *adapters):
        self.adapters = [to_adapter(a) for a in adapters]

    def __call__(self, context):
        return [a(context) for a in self.adapters]

class ConvertAdapter(object):

    def __init__(self, adapter, a2=None, factor=1, offset=0):
        self.adapter = to_adapter(adapter, a2=a2)
        self.factor = factor
        self.offset = offset

    def __call__(self, context):
        value = self.adapter(context)
        return value * self.factor + self.offset

def StickAxis(adapter, a2=None):
    return ConvertAdapter(adapter, a2=a2, factor=1/32768)

def TriggerAxis(adapter, a2=None):
    return ConvertAdapter(adapter, a2=a2, factor=1/65535, offset=.5)

def InvertAxis(adapter, a2=None):
    return ConvertAdapter(adapter, a2=a2, factor=-1)

def InvertButton(adapter, a2=None):
    return ConvertAdapter(adapter, a2=a2, factor=-1, offset=1)


def to_adapter(a, a2=None):
    if callable(a):
        return a
    if isinstance(a, tuple) and len(a) > 0 and callable(a[0]):
        return GroupAdapter(*a)
    if not isinstance(a, tuple) or len(a) != 2:
        if isinstance(a, int) and a2 is not None:
            a = (a, a2)
        else:
            raise TypeError(repr(a) + " is not a valid control spec")
    return SimpleStateAdapter(a)


class Control(object):

    def __init__(self, source, look):
        self.source = to_adapter(source)
        self.look = look

    def init_theme(self, theme):
        return self.look.init_theme(theme)

    def update(self, context):
        return self.look.update(context, self.source(context))

    def draw(self, cctx):
        return self.look.draw(cctx)


class Layout(object):

    def __init__(self, c):
        self.controls = self.create_controls(c)

    def create_controls(self, c):
        raise NotImplementedError()


class Theme(object):
    pass


class ControllerType(object):

    def __getattr__(self, name):
        if name == 'STL':
            return (self.STL_X, self.STL_Y, self.STL_B)
        elif name == 'STR':
            return (self.STR_X, self.STR_Y, self.STR_B)
        elif name == 'DPAD':
            return (self.DPAD_X, self.DPAD_Y)
        else:
            raise AttributeError


CONTROLLER_TYPES = {}
LAYOUTS = {}
THEMES = {}

def import_config_from_module(module):
    for v in vars(module).values():
        try:
            if issubclass(v, Layout) and v != Layout:
                LAYOUTS[v.name] = v
            elif issubclass(v, Theme) and v != Theme:
                THEMES[v.name] = v
            elif issubclass(v, ControllerType) and v != ControllerType:
                CONTROLLER_TYPES[v.name] = v
        except TypeError:
            pass


# vim:set sw=4 ts=8 sts=4 et sr ft=python fdm=marker tw=0:
