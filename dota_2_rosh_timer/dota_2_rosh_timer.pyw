"""
DotA 2 Roshan death timer macros, using computer vision. Tracks expiration time, minimum and
maximum respawn timer as contents of your clipboard. Handy in combination with Win+V hotkey.
Should work on any 1920x1080 screen.

You may or may not get VAC-banned for using this in your games. Use on your own risk.
"""

from datetime import timedelta
from itertools import accumulate

import easyocr
import numpy as np
import pyperclip
from PIL import ImageGrab

SECONDS_IN_A_MINUTE = 60


def main() -> None:
    # Numbers here indicate the approximate location of the DotA timer
    timer = np.asarray(ImageGrab.grab(bbox=(937, 24, 983, 35)))
    timer = easyocr.Reader(["en"]).readtext(timer)[0][1].replace(".", ":").replace(",", ":")

    minutes_seconds = map(int, timer.split(":"))
    times = accumulate(
        [
            timedelta(minutes=next(minutes_seconds), seconds=next(minutes_seconds)),
            timedelta(minutes=5),
            timedelta(minutes=3),
            timedelta(minutes=3),
        ]
    )
    # Convert an iterator of Python timedelta objects into a generator of DotA-type timers.
    # Single-digit values are zero-padded.
    times = (
        ":".join((str(j).zfill(2) for j in divmod(i.seconds, SECONDS_IN_A_MINUTE)))
        for i in times
    )
    pyperclip.copy(" -> ".join(times))


if __name__ == "__main__":
    main()
