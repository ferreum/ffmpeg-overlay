#!/usr/bin/python

from overlayapi import (ControllerType, Layout, Theme, Control,
                        StickAxis, TriggerAxis,
                        StickLook, CircleLook, RectLook, DpadGroupLook)


class CTypeXpad(ControllerType):
    name = 'xpad'

    """These tuple's values are:
    (type, number)
    type - the type field of jstest --events
    number - the number field of jstest --events"""

    A = (1, 0)
    B = (1, 1)
    X = (1, 2)
    Y = (1, 3)
    STL_X = StickAxis(2, 0)
    STL_Y = StickAxis(2, 1)
    STL_B = (1, 9)
    STR_X = StickAxis(2, 3)
    STR_Y = StickAxis(2, 4)
    STR_B = (1, 10)
    DPAD_X = StickAxis(2, 6)
    DPAD_Y = StickAxis(2, 7)
    LB = (1, 4)
    RB = (1, 5)
    LT = TriggerAxis(2, 2)
    RT = TriggerAxis(2, 5)
    BACK = (1, 6)
    START = (1, 7)
    GUIDE = (1, 8)

    @staticmethod
    def match_name(line):
        return "X-Box One pad" in line


class CTypeXboxdrv(ControllerType):
    name = 'xboxdrv'

    A = (1, 0)
    B = (1, 1)
    X = (1, 2)
    Y = (1, 3)
    STL_X = StickAxis(2, 0)
    STL_Y = StickAxis(2, 1)
    STL_B = (1, 9)
    STR_X = StickAxis(2, 2)
    STR_Y = StickAxis(2, 3)
    STR_B = (1, 10)
    DPAD_X = StickAxis(2, 6)
    DPAD_Y = StickAxis(2, 7)
    LB = (1, 4)
    RB = (1, 5)
    LT = TriggerAxis(2, 5)
    RT = TriggerAxis(2, 4)
    BACK = (1, 6)
    START = (1, 7)
    GUIDE = (1, 8)

    @staticmethod
    def match_name(line):
        return "Xbox Gamepad (userspace driver)" in line


class DistanceLayout(Layout):
    name = 'distance'

    scale = 12
    width = 35
    height = 8

    def create_controls(self, c):

        """Return the list of controls for the overlay.

        c is the current controller type."""

        hidetime = 3000
        smallabel = {'size':.7}
        controls = [
            Control(c.DPAD, DpadGroupLook((4, 4), 4 * .8, hidetime=hidetime)),
            Control(c.STL, StickLook((16.2, 4), 4)),
            Control(c.STR, StickLook((23.8, 4), 4)),
            Control(c.A, CircleLook((33, 7), 1, hidetime=hidetime, label='A')),
            Control(c.B, CircleLook((33, 5), 1, hidetime=hidetime, label='B')),
            Control(c.X, CircleLook((33, 3), 1, hidetime=hidetime, label='X')),
            Control(c.Y, CircleLook((33, 1), 1, hidetime=hidetime, label='Y')),
            Control(c.LB, RectLook((10, 2), (4, 2), label='JMP')),
            Control(c.LT, RectLook((10, 6), (4, 2), label='BRK')),
            Control(c.RB, RectLook((30, 6), (4, 2), label='BST')),
            Control(c.RT, RectLook((30, 2), (4, 2), label='FWD')),
            Control(c.BACK, RectLook((10, 4), (3, 1.5), hidetime=hidetime, label='RST', labelargs=smallabel)),
            Control(c.START, RectLook((30, 4), (3, 1.5), hidetime=hidetime, label='MNU', labelargs=smallabel)),
        ]
        return controls


class DefaultTheme(Theme):
    name = 'default'

    bgcolor = (.28, .28, .28)
    fgcolor = (.5, .5, .5)
    maxedcolor = (.94, .94, .94)
    textcolor = (.75, .75, .75)


class LightTheme(Theme):
    name = 'light'

    bgcolor = (.28, .28, .28)
    fgcolor = (.94, .94, .94)
    maxedcolor = (.88, .88, 1.)
    textcolor = (.5, .5, .5)


class DarkTheme(Theme):
    name = 'dark'

    bgcolor = (.06, .06, .06)
    fgcolor = (.12, .12, .12)
    maxedcolor = (.25, .25, .25)
    textcolor = (.75, .75, .75)


class ContrastTheme(Theme):
    name = 'contrast'

    bgcolor = (.06, .06, .06)
    fgcolor = (0., 0., 0.)
    maxedcolor = (.25, .25, .25)
    textcolor = (.75, .75, .75)


# vim:set sw=4 ts=8 sts=4 et sr ft=python fdm=marker tw=0:
