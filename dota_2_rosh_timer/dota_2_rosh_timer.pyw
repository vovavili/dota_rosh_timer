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

import gzip
import json
import pickle
import re
from collections.abc import Iterable
from datetime import datetime, timedelta
from enum import Enum
from itertools import accumulate
from pathlib import Path
from typing import Optional
from urllib.request import urlopen

import easyocr
import numpy as np
import pyperclip
import typer
from PIL import ImageGrab
from typer import Argument

GREEN_TERMINAL = "\033[92m"
SECONDS_IN_A_MINUTE = 60
CACHE_DIR = Path().absolute() / "cache"


class ToTrack(str, Enum):
    """All the possible main function arguments."""

    ROSHAN = "roshan"
    GLYPH = "glyph"
    BUYBACK = "buyback"
    ITEM = "item"
    ABILITY = "ability"


def _timedelta_to_dota_timer(
    arr_of_deltas: Iterable[timedelta], prefix: str = "", timers_sep: str = " -> "
) -> str:
    """Convert an itertable of Python timedelta objects into a string of joined
    and delineated DotA-type timers. Single-digit values are zero-padded."""
    return (
        prefix
        + (" " if prefix else "")
        + timers_sep.join(
            ":".join(
                (
                    str(time_unit).zfill(2)
                    for time_unit in divmod(delta.seconds, SECONDS_IN_A_MINUTE)
                )
            )
            for delta in arr_of_deltas
        )
    )


def _get_cooldowns(constant_type: str, item_or_ability: str) -> int | list[str]:
    """A shorthand for querying cooldowns from the OpenDota constants database. To reduce the load
    on GitHub servers and waste less traffic, queries are cached and are updated every other day."""
    try:
        # Check whether the locally stored cache needs an update
        with gzip.open(CACHE_DIR / (constant_type + "_timestamp.gz"), "rb") as file:
            update_threshold = pickle.load(file)

        assert datetime.now() > update_threshold

        # Load the locally stored cache
        with gzip.open(CACHE_DIR / (constant_type + "_cache.gz"), "rb") as file:
            data = pickle.load(file)
    except (FileNotFoundError, AssertionError):
        data = json.loads(
            urlopen(
                "https://raw.githubusercontent.com/odota/dotaconstants/master/build/"
                + constant_type
                + ".json"
            ).read()
        )
        update_threshold = datetime.now() + timedelta(days=2)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with gzip.open(CACHE_DIR / (constant_type + "_timestamp.gz"), "wb") as file:
            pickle.dump(update_threshold, file, protocol=pickle.HIGHEST_PROTOCOL)
        with gzip.open(CACHE_DIR / (constant_type + "_cache.gz"), "wb") as file:
            pickle.dump(data, file, protocol=pickle.HIGHEST_PROTOCOL)
    return data[item_or_ability]["cd"]


def main(
    to_track: ToTrack = Argument(
        ToTrack.ROSHAN, help="Specify the kind of information you want to track."
    ),
    item_or_ability: Optional[str] = Argument(
        None,
        help="Specify the cooldown of what item or ability you want to track. "
        "For abilities, make sure to prefix the hero name (e.g. `faceless_void_chronosphere`).",
    ),
) -> None:
    """The main function. One can pass a command-line argument to track other metrics here."""
    print("Running...")
    to_track = to_track.casefold().strip()
    if item_or_ability is not None:
        item_or_ability = item_or_ability.casefold().strip()
    timers_sep = " -> "
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
        case ToTrack.ITEM:
            cooldown = _get_cooldowns("items", item_or_ability)
            times = [timedelta(seconds=cooldown)]
            to_track = item_or_ability.replace("_", " ")
        case ToTrack.ABILITY:
            cooldown = _get_cooldowns("abilities", item_or_ability)
            if isinstance(cooldown, int):
                times = [timedelta(seconds=cooldown)]
            else:
                timers_sep = " || "  # TODO: make this more informative in the future
                times = [timedelta(seconds=int(i)) for i in cooldown]
                to_track = item_or_ability.replace("_", " ")
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
    pyperclip.copy(
        _timedelta_to_dota_timer(times, prefix=to_track, timers_sep=timers_sep)
    )
    print(GREEN_TERMINAL + "Done!")


if __name__ == "__main__":
    typer.run(main)
