"""
DotA 2 Roshan death timer macros, using computer vision. Tracks expiration time, minimum
and maximum respawn timer as contents of your clipboard. Handy in combination with Win+V
clipboard hotkey. Should work on any 1920x1080 screen.

You may or may not get VAC-banned for using this in your games, though I presume that a ban
is unlikely as you are not interacting with DotA files in any direct or indirect way.
Use on your own risk.

By default, this tracks the Roshan timer. One can also specify command line arguments to track
metrics like glyph, buyback, item and ability cooldowns.
"""

import gzip
import itertools
import json
import pickle
import string
from collections.abc import Iterable
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Final, Optional, Literal
from urllib.request import urlopen

import easyocr
import numpy as np
import pyperclip
import typer
from PIL import ImageGrab
from typer import Argument

SECONDS_IN_A_MINUTE: Final[int] = 60
CACHE_DIR: Final[Path] = Path().absolute() / "cache"


class ToTrack(str, Enum):
    """All the possible main function arguments."""

    ROSHAN = "roshan"
    GLYPH = "glyph"
    BUYBACK = "buyback"
    ITEM = "item"
    ABILITY = "ability"


def _timedelta_to_dota_timer(
    arr_of_deltas: Iterable[timedelta],
    timers_sep: Literal[" -> ", " || "],
    prefix: str = "",
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
                    for time_unit in divmod(
                        int(delta.total_seconds()), SECONDS_IN_A_MINUTE
                    )
                )
            )
            for delta in arr_of_deltas
        )
    )


def _get_cooldowns(constant_type: str, item_or_ability: str) -> int | list[str]:
    """A shorthand for querying cooldowns from the OpenDota constants database. To reduce the load
    on GitHub servers and waste less traffic, queries are cached and are updated every other day."""
    try:
        assert item_or_ability is not None
    except AssertionError as error:
        raise AssertionError(
            "Missing item or ability command line parameter."
        ) from error
    try:
        # Check whether the locally stored cache needs an update
        with gzip.open(
            CACHE_DIR / (constant_type + "_timestamp.gz"), "rb"
        ) as timestamp_file:
            assert datetime.now() > pickle.load(timestamp_file)

        # Load the locally stored cache, if it exists
        with gzip.open(CACHE_DIR / (constant_type + "_cache.gz"), "rb") as cache_file:
            data = pickle.load(cache_file)
    except (FileNotFoundError, AssertionError):
        with urlopen(
            "https://raw.githubusercontent.com/odota/dotaconstants/master/build/"
            + constant_type
            + ".json"
        ) as opendota_link:
            data = json.loads(opendota_link.read())
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with gzip.open(
            CACHE_DIR / (constant_type + "_timestamp.gz"), "wb"
        ) as timestamp_file:
            pickle.dump(
                datetime.now() + timedelta(days=2),
                timestamp_file,
                protocol=pickle.HIGHEST_PROTOCOL,
            )
        with gzip.open(CACHE_DIR / (constant_type + "_cache.gz"), "wb") as cache_file:
            pickle.dump(data, cache_file, protocol=pickle.HIGHEST_PROTOCOL)
    try:
        return data[item_or_ability]["cd"]
    except KeyError as error:
        raise KeyError(
            "This ability or item does not exist in the OpenDotA constants "
            "database, or it doesn't have a cooldown. Maybe you misspelled it? "
            "Make sure to prefix the hero name for abilities "
            "(e.g. `faceless_void_chronosphere`)."
        ) from error


def main(
    to_track: ToTrack = Argument(
        ToTrack.ROSHAN,
        help="Specify the kind of information you want to track. If no argument "
        "is specified, Roshan death time is tracked.",
    ),
    item_or_ability: Optional[str] = Argument(
        None,
        help="Specify the cooldown of what item or ability you want to track. "
        "For abilities, make sure to prefix the hero name (e.g. `faceless_void_chronosphere`).",
    ),
) -> None:
    """The main function. One can pass a command-line argument to track other metrics here."""
    typer.echo("Running...")
    to_track = to_track.casefold()
    if item_or_ability is not None:
        item_or_ability = item_or_ability.casefold()
    # I need to cast a type here due to an old-standing bug in PyCharm with literal arguments
    timers_sep: Literal[" -> "] = " -> "
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
        case ToTrack.ITEM | ToTrack.ABILITY:
            cooldown = _get_cooldowns(
                "items" if to_track == ToTrack.ITEM else "abilities", item_or_ability
            )
            to_track = item_or_ability.replace("_", " ")
            if isinstance(cooldown, int):
                times = [timedelta(seconds=cooldown)]
            else:
                timers_sep: Literal[" || "] = " || "
                times = [timedelta(seconds=int(i)) for i in cooldown]
        case _:
            raise ValueError(
                "Unsupported command line argument. Please use `--help` for "
                "a list of all supported commands."
            )

    # Numbers here indicate the approximate location of the DotA timer
    timer = np.asarray(ImageGrab.grab(bbox=(937, 24, 983, 35)))  # NOQA
    timer = easyocr.Reader(["en"]).readtext(timer, allowlist=string.digits + ":")[0][1]

    minutes_seconds = map(int, timer.split(":"))
    times = itertools.accumulate(
        [timedelta(minutes=next(minutes_seconds), seconds=next(minutes_seconds))]
        + times
    )
    pyperclip.copy(
        _timedelta_to_dota_timer(times, timers_sep=timers_sep, prefix=to_track)
    )
    typer.secho("Done!", fg=typer.colors.GREEN)


if __name__ == "__main__":
    typer.run(main)
