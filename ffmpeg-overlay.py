#!/usr/bin/python

import cairocffi as cairo
import sys
import os
import contextlib
import overlayapi as api
import js
from overlayapi import Context, ControlsAnimation
from common import ArgvError


class FFMpegWriter(object):

    def __init__(self, surface, cctx, templateargs, position=(.5, 1.0),
                 fps=30, unpremultiply="unpremultiply"):
        self.surface = surface
        self.cctx = cctx
        self.templateargs = templateargs
        self.position = position
        self.fps = fps
        self.unpremultiply = unpremultiply

        self.frame_size = (surface.get_width(), surface.get_height())
        self.frame_format = "bgra"

    @contextlib.contextmanager
    def saving(self):
        self.setup()
        try:
            yield
        except BrokenPipeError:
            raise
        except:
            # Need to terminate ffmpeg here because it seems to ignore the
            # overlay if no video data was sent, producing a video without
            # overlay in case of an error.
            self._proc_ff.terminate()
            raise
        finally:
            self.wait()

    def setup(self):
        self._run()

    def _run(self):
        import subprocess
        try:
            pass_fds = [int(fd) for fd in os.environ['FFMPEG_OVERLAY_FDS'].split(",")]
        except KeyError:
            pass_fds = []
        pread, pwrite = os.pipe()
        try:
            pass_fds.append(pread)
            ffenv = dict(os.environ)
            ffenv['FFMPEG_OVERLAY_FDS'] = ','.join(str(fd) for fd in pass_fds)
            command = self._args(pread)
            self._proc_filter = subprocess.Popen((self.unpremultiply,), shell=False,
                                                stdin=subprocess.PIPE,
                                                stdout=pwrite,
                                                stderr=sys.stderr)
            self._proc_ff = subprocess.Popen(command, shell=False,
                                            pass_fds=pass_fds,
                                            env=ffenv,
                                            stdin=sys.stdin,
                                            stdout=sys.stdout,
                                            stderr=sys.stderr)
        finally:
            os.close(pread)
            os.close(pwrite)
        self._stream = self._proc_filter.stdin

    def _args(self, pread):
        args = []
        haveinput = False
        for arg in self.templateargs:
            if arg.startswith("{{") and arg.endswith("}}"):
                args.append(arg[1:-1])
            elif arg in ('{overlay}', '{overlayin}', '{overlayfilter}'):
                if arg in ('{overlay}', '{overlayin}'):
                    args += ['-f', 'rawvideo', '-vcodec', 'rawvideo',
                             '-s', '%dx%d' % self.frame_size, '-pix_fmt',
                             self.frame_format, '-r', str(self.fps), '-i', 'pipe:%s' % (pread,)]
                    haveinput = True
                if arg in ('{overlay}', '{overlayfilter}'):
                    pos = self.position
                    args += ['-lavfi',
                             'overlay=(W-w)*{left}:(H-h)*{top}:shortest=1'.format(
                             left=pos[0], top=pos[1])]
            else:
                args.append(arg)
        if not haveinput:
            raise ValueError("no overlay placeholder found")
        return args

    def save_frame(self):
        surface = self.surface
        cctx = self.cctx
        surface.flush()
        self._stream.write(surface.get_data())
        with cctx:
            cctx.set_source_rgba(0, 0, 0, 0)
            cctx.set_operator(cairo.OPERATOR_SOURCE)
            cctx.paint()

    def wait(self):
        try:
            self._stream.close()
        except BrokenPipeError:
            # This means the pipeline exited before we got here.
            pass
        proc = self._proc_ff
        # I really want to wait for this process first.
        while True:
            try:
                status = proc.wait()
                self.exit_status = status
                return status
            except KeyboardInterrupt:
                # ffmpeg receives these signals and exits at some point,
                # just keep waiting
                pass


def convert_timearg(s):
    if s is not None:
        return int(float(s) * 1000)
    else:
        return 0


def parse_args(argv):
    progname = argv.pop(0).rpartition('/')[2]
    try:
        index = argv.index('--')
        templateargs = argv[index + 1:]
        argv = argv[:index]
    except ValueError:
        # Handle missing template later so we can be called with -h.
        templateargs = None

    import argparse
    parser = argparse.ArgumentParser(prog=progname, epilog="""
    Use -- to separate the command template from arguments for this script.

    The first occurrence of {overlay} is replaced with ffmpeg input options
    for reading the overlay from stdin. This marker must follow the first
    input, which is used as main video.

    All occurrences of {ss} are replaced with the value of the --start option
    in ffmpeg-compatible time format. If no --start option is given, 0 is used.
    """)
    parser.add_argument('-e', '--events', help="jstest --event output file")
    parser.add_argument('-d', '--delay', default=None,
                        help="Additional delay for events in seconds (float)")
    parser.add_argument('-s', '-ss', '--start', default=None, dest='start',
                        help="Skip given amount of time of events, in seconds. For use with ffmpeg -ss option")
    parser.add_argument('-S', '--absolute-start', default=None, dest='absolute_start',
                        help="Absolute start time within events")
    parser.add_argument('-t', '--type', default='auto', help="Specify the controller type to use")
    parser.add_argument('-l', '--layout', default='distance', help="Name of the layout to use")
    parser.add_argument('-T', '--theme', default='default', help="Specify the theme to use")
    parser.add_argument('--scale', type=float, default=1.0, help="Scale the overlay by the given value")
    parser.add_argument('-r', '--fps', type=int, default=60, help="Framerate at which the overlay is generated")
    parser.add_argument('-p', '--position', default="1.0,0.8", metavar="LEFT,TOP", help="Relative position of the overlay, values between 0.0 and 1.0")
    parser.add_argument('--unpremultiply', default="unpremultiply", help="Override the command name of unpremultiply")

    args = parser.parse_args(argv)

    api.import_all_config()

    args.delay = convert_timearg(args.delay)
    args.start = convert_timearg(args.start)
    if args.absolute_start is not None:
        args.absstart = int(args.absolute_start)
    else:
        args.absstart = 0

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

    left, sep, top = args.position.partition(",")
    if sep == "":
        raise ArgvError("invalid position: %s" % (args.position,), parser)
    args.position = (left, top)

    if templateargs is None:
        raise ArgvError("ffmpeg arguments not specified", parser)
    else:
        templateargs = [str(args.start / 1000) if s == "{ss}" else s for s in templateargs]
        args.templateargs = templateargs

    return layoutcls, ctype, theme, args


def create_surface(layout, scale):
    scale = layout.scale * scale
    img = cairo.ImageSurface(cairo.FORMAT_ARGB32,
            int(layout.width * scale),
            int(layout.height * scale))
    cctx = cairo.Context(img)
    cctx.scale(scale)
    return img, cctx


def main(argv):
    layoutcls, ctype, theme, args = parse_args(argv)
    layout = layoutcls(ctype)

    surface, cctx = create_surface(layout, args.scale)
    with open(args.events, 'r') as source:
        context = Context(theme, ctype, js.HandlerJsEvents(source))
        context.init_time(args.start - args.delay, absstart=args.absstart)

        anim = ControlsAnimation(context, layout.controls, fps=args.fps)

        writer = FFMpegWriter(surface, cctx, args.templateargs,
                              position=args.position, fps=args.fps,
                              unpremultiply=args.unpremultiply)
        try:
            anim.save(writer)
        except BrokenPipeError:
            pass
        return writer.exit_status

if __name__ == '__main__':
    from common import run_main
    run_main(main)
