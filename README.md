ffmpeg-overlay.py - ffmpeg wrapper for gamecontroller overlays.
===============================================================

## Dependencies

Needs Python 3, tested with Python 3.5.1
Needs the cairocffi python module.
Expects `unpremultiply` to be in the `$PATH`.
For recording the evnets, use the `jstest` program.

### Install cairocffi

Check your repository for cairocffi or install it using pip:

    pip install --user cairocffi
    # omit --user for system-wide installation

### Building unpremultiply

    cc -Wall -O2 -o unpremultiply unpremultiply.c

ffmpeg-overlay.py expects unpremultiply to be in the current PATH.

    # assuming unpremultiply is in the current
    # directory, like after the build step
    export PATH=$PWD:$PATH

## Usage

While recording the video, record the events using the jstest program:

    stdbuf -oL jstest --event "/dev/input/js1" >events.jse

Change to your js device accordingly. Use ctrl-c to stop recording.
`stdbuf` is used here to prevent the last few events from being dropped
when the program is killed.

After recording, use the `ffmpeg-overlay.py` script to re-encode the video with overlay:

    ffmpeg-overlay.py -e events.jse -t xboxdrv --pos 1,.8 -- ffmpeg -i recorded-video.mkv '{overlayin}' -c:v libx264 -crf 23 -y output-video.mkv

The basic usage here is

    ffmpeg-overlay.py -e <eventsfile> [options] -- <ffmpeg commandline>

The special argument `{overlayin}` is replaced with the options for ffmpeg to
receive the generated overlay, including a video filter. This value must follow
the first input file, because the filter expects the first input to be the main video
and the second input to be the overlay.

### Controller type, layout and theme

Specify your controller type with the `-t` option. If there is no match for
your controller, see [Advanced configuration](#advanced-configuration).
Use `-l` and `-T` respectively to specify layout and theme.

### Syncing

The events and the video will probably be offset by a certain time.
For this there exists the `-d` option to delay the events.

    # delay all events by 0.3 seconds
    ffmpeg-overlay.py -e events.jse -d 0.3 ...
    # make all events appear 0.2 seconds earlier
    ffmpeg-overlay.py -e events.jse -d -0.2 ...

Notice that the absolute times recorded by jstest do not matter, as all times
are used relative to the time of the first event.

### Cut the video at the start

To start the video (and the overlay) at a different point, use the `-s` option.
There exists another special value for the ffmpeg commandline to aid with this:
`{ss}` is replaced with the same value given to `-s` such that ffmpeg's `-ss`
option understands it.

    ffmpeg-overlay.py -e events.jse -d 0.3 -s 15.3 -- ffmpeg -ss '{ss}' -i recorded-video.mkv '{overlayin}' -c:v libx264 -crf 23 -y output-video.mkv

This starts the video at 15.3 seconds with events delayed by 0.3 seconds.
Notice that the `-ss` option needs to be specified before the main video file.

## Advanced configuration

ffmpeg-overlay.py sources the file `$XDG_CONFIG_HOME/ffmpeg-overlay/config.py`
if it exists. Custom controller types, layouts and themes can be specified
here. See `defaults.py` for examples.
