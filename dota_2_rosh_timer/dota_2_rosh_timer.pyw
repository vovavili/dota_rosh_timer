"""
DotA 2 Roshan death timer macros, using computer vision. Tracks expiration time, minimum
and maximum respawn timer as contents of your clipboard. Handy in combination with Win+V
clipboard hotkey. Should work on any 1920x1080 screen.

You may or may not get VAC-banned for using this in your games, though I presume that a ban
is unlikely as you are not interacting with DotA files in any direct or indirect way.
Use on your own risk.

By default, this tracks the Roshan timer. One can also specify command line arguments to track
metrics like glyph and buyback cooldowns.
"""

import re
from collections.abc import Iterable
from datetime import timedelta
from enum import Enum
from itertools import accumulate

import easyocr
import numpy as np
import pyperclip
import typer
from PIL import ImageGrab

SECONDS_IN_A_MINUTE = 60


class ToTrack(str, Enum):
    """All the possible arguments as an Enum class, done for type safety."""

    ROSHAN = "roshan"
    GLYPH = "glyph"
    BUYBACK = "buyback"


def _timedelta_to_dota_timer(
    arr_of_deltas: Iterable[timedelta], prefix: str = "", sep: str = " -> "
) -> str:
    """Convert an itertable of Python timedelta objects into a string of joined
    and delineated DotA-type timers. Single-digit values are zero-padded."""
    return (
        prefix
        + (" " if prefix else "")
        + sep.join(
            ":".join(
                (
                    str(time_unit).zfill(2)
                    for time_unit in divmod(delta.seconds, SECONDS_IN_A_MINUTE)
                )
            )
            for delta in arr_of_deltas
        )
    )


def main(to_track: ToTrack = typer.Argument(ToTrack.ROSHAN)) -> None:
    """The main function. One can pass an argument to track other metrics here."""
    to_track = to_track.casefold().strip()
    match to_track:
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
    timer = easyocr.Reader(["en"]).readtext(timer)[0][1].strip()
    timer = re.sub(r"\W", ":", timer)
    timer = re.sub(r"[^\d:]", "", timer)

    minutes_seconds = map(int, timer.split(":"))
    times = accumulate(
        [timedelta(minutes=next(minutes_seconds), seconds=next(minutes_seconds))]
        + times
    )
    pyperclip.copy(_timedelta_to_dota_timer(times, prefix=to_track))


if __name__ == "__main__":
    typer.run(main)
