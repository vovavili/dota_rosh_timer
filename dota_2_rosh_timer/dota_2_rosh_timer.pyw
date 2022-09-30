"""
DotA 2 Roshan death timer macros, using computer vision. Tracks expiration time, minimum and
maximum respawn timer as contents of your clipboard. Handy in combination with Win+V hotkey.
Should work on any 1920x1080 screen.

You may or may not get VAC-banned for using this in your games. Use on your own risk.
"""

from enum import Enum
from datetime import timedelta
from itertools import accumulate

import typer
import easyocr
import numpy as np
import pyperclip
from PIL import ImageGrab

SECONDS_IN_A_MINUTE = 60


class ToTrack(str, Enum):
    ROSHAN = "roshan"
    GLYPH = "glyph"
    BUYBACK = "buyback"


def main(to_track: ToTrack = typer.Argument(ToTrack.ROSHAN)) -> None:
    """The main function. One can pass an argument to track other metrics here."""
    match to_track.casefold().strip():
        case ToTrack.ROSHAN:
            times = [
                timedelta(minutes=5),
                timedelta(minutes=3),
                timedelta(minutes=3),
            ]
        case ToTrack.GLYPH:
            times = [timedelta(minutes=5)]
        case ToTrack.BUYBACK:
            times = [timedelta(minutes=8)]
        case _:
            times = []
            assert ValueError("Unsupported command line argument.")

    # Numbers here indicate the approximate location of the DotA timer
    timer = np.asarray(ImageGrab.grab(bbox=(937, 24, 983, 35)))  # NOQA
    timer = (
        easyocr.Reader(["en"]).readtext(timer)[0][1].replace(".", ":").replace(",", ":")
    )

    minutes_seconds = map(int, timer.split(":"))
    times = accumulate(
        [timedelta(minutes=next(minutes_seconds), seconds=next(minutes_seconds))]
        + times
    )
    # Convert an iterator of Python timedelta objects into a generator of DotA-type timers.
    # Single-digit values are zero-padded.
    times = (
        ":".join((str(j).zfill(2) for j in divmod(i.seconds, SECONDS_IN_A_MINUTE)))
        for i in times
    )
    pyperclip.copy(" -> ".join(times))


if __name__ == "__main__":
    typer.run(main)
