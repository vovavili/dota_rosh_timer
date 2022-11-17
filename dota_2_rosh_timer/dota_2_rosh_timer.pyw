#!/usr/bin/env python
"""
DotA 2 Roshan death timer macros, using computer vision. Tracks expiration time, minimum
and maximum respawn timer as contents of your clipboard. Handy in combination with Win+V
clipboard hotkey. Should work on any 1920x1080 screen, other monitor sizes not tested.

You may or may not get VAC-banned for using this in your games, though I presume that a
ban is unlikely as you are not interacting with DotA files in any direct or indirect
way. Use on your own risk.

By default, this tracks the Roshan timer. One can also specify command line arguments to
track metrics like glyph, buyback, item and ability cooldowns.
"""

from __future__ import annotations

import gettext
import itertools
import os
import string
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from enum import Enum
from functools import partial, wraps
from gettext import gettext as _
from pathlib import Path
from typing import Final, Literal, Optional, ParamSpec, TypeVar
from urllib.error import HTTPError
from urllib.request import urlopen

import cv2 as cv
import easyocr
import numpy as np
import numpy.typing as npt
import pyperclip
import screeninfo
import simdjson
import typer
from PIL import ImageGrab
from simdjson import Parser

T = TypeVar("T")
P = ParamSpec("P")

HOME_DIR: Final[Path] = Path(__file__).resolve().parents[1]


class Language(str, Enum):
    """Languages for timer output."""

    ENGLISH = "english"
    RUSSIAN = "russian"
    SPANISH = "spanish"


class ToTrack(str, Enum):
    """All the valid main function arguments."""

    ROSHAN = "roshan"
    GLYPH = "glyph"
    BUYBACK = "buyback"
    ITEM = "item"
    ABILITY = "ability"

    @property
    def plural(self: Literal[ToTrack.ITEM, ToTrack.ABILITY]) -> str:
        """Get a pluralized form of the string."""
        return "items" if self is ToTrack.ITEM else "abilities"

    @property
    def times(
        self: Literal[ToTrack.ROSHAN, ToTrack.GLYPH, ToTrack.BUYBACK]
    ) -> list[timedelta]:
        """Get corresponding time splits for a constant."""
        match self:
            case ToTrack.ROSHAN:
                return [
                    timedelta(minutes=5),
                    timedelta(minutes=3),
                    timedelta(minutes=3),
                ]
            case ToTrack.GLYPH:
                return [timedelta(minutes=5)]
            case ToTrack.BUYBACK:
                return [timedelta(minutes=8)]


class TimersSep(str, Enum):
    """All the valid timers separators."""

    ARROW = " -> "
    PIPE = " || "


def enter_subdir(subdir: str) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """During the execution of a function, temporarily enter a subdirectory."""

    def decorator(function: Callable[P, T]) -> Callable[P, T]:
        @wraps(function)
        def wrapper(*args, **kwargs) -> T:
            old_dir, new_dir = Path.cwd(), HOME_DIR / subdir
            new_dir.mkdir(parents=True, exist_ok=True)
            os.chdir(new_dir)
            return_value = function(*args, **kwargs)
            os.chdir(old_dir)
            return return_value

        return wrapper

    return decorator


def timedelta_to_dota_timer(delta: timedelta) -> str:
    """Convert a timedelta into a DotA timer string. Seconds are zero-padded."""
    delta = [str(t) for t in divmod(int(delta.total_seconds()), 60)]
    delta[-1] = delta[-1].zfill(2)
    return ":".join(delta)


def process_timedeltas(
    arr_of_deltas: Iterable[timedelta],
    prefix: str,
    timers_sep: TimersSep,
    sep_prefix: Iterable[str] | None,
) -> str:
    """Convert an itertable of timedeltas into a string of joined and delineated
    DotA-type timers."""
    times = map(timedelta_to_dota_timer, arr_of_deltas)
    if sep_prefix is not None:
        times = (" ".join(t) for t in zip(sep_prefix, times))
    return prefix + " " + timers_sep.join(times)


def make_update_timestamp(filename: str, days: int, patch: str) -> None:
    """Set the time threshold at which the cache timestamp has to be checked."""
    timestamp = datetime.now() + timedelta(days=days)
    timestamp = simdjson.dumps({"timestamp": timestamp.isoformat(), "patch": patch})
    with open(filename, "w", encoding="utf-8") as file:
        file.write(timestamp)


def get_latest_patch() -> str:
    """Get the latest available DotA 2 patch."""
    with urlopen(
        "https://raw.githubusercontent.com/odota/dotaconstants/master/"
        "build/patchnotes.json"
    ) as patchnotes_link:
        *_, patch = Parser().parse(patchnotes_link.read()).keys()
    return patch


@enter_subdir("cache")
def get_cooldowns(
    constant_type: str, item_or_ability: str | None, force_update: bool
) -> str | Iterable[str]:
    """A shorthand for querying cooldowns from the OpenDota constants database. To
    reduce the load on GitHub servers and waste less traffic, queries are cached and
    are updated when there is a new patch only. Caching is done with simdjson, an
    extremely fast JSON parser."""
    if item_or_ability is None:
        raise ValueError(
            f"Missing item or ability command line parameter for constant type "
            f"{constant_type}."
        )
    data, patch, timestamp_filename, cache_filename = (
        {},
        None,
        constant_type + "_timestamp.json",
        constant_type + "_cache.json",
    )
    update_timestamp = partial(make_update_timestamp, timestamp_filename, 2)
    try:
        assert not force_update
        # Check whether the locally stored cache needs an update
        timestamp = Parser().load(timestamp_filename)
        # Only prune cache if new patch has been released
        if datetime.now() > datetime.fromisoformat(timestamp["timestamp"]):
            patch = get_latest_patch()
            assert patch == timestamp["patch"]
            update_timestamp(patch)
        # Load the locally stored cache, if it exists
        data = Parser().load(cache_filename)
    except (FileNotFoundError, OSError, AssertionError, KeyError):
        with urlopen(
            "https://raw.githubusercontent.com/odota/dotaconstants/master/build/"
            + constant_type
            + ".json"
        ) as opendota_link:
            try:
                data = Parser().parse(opendota_link.read())
            except HTTPError as error:
                raise ValueError(
                    f'Constant type "{constant_type}" does not exist in '
                    f"the OpenDotA constants database."
                ) from error
        if patch is None:
            patch = get_latest_patch()
        update_timestamp(patch)
        with open(cache_filename, "wb") as file:
            file.write(data.mini)  # NOQA
    try:
        return data[item_or_ability]["cd"]
    except KeyError as error:
        raise KeyError(
            "This ability or item does not exist in the OpenDotA constants "
            "database, or it doesn't have a cooldown. Maybe you misspelled it? "
            "Make sure to prefix the hero name for abilities "
            "(e.g. `faceless_void_chronosphere`)."
        ) from error


def screenshot_dota_timer() -> npt.NDArray[np.uint8]:
    """Make and process a screenshot of the DotA timer, regardless of screen size
    and operating system. Only tested for 1920x1080 monitor."""
    info = next(s for s in screeninfo.get_monitors() if s.is_primary)
    half_width, height = info.width // 2, info.height
    offset = half_width // 40

    # Numbers here indicate the approximate location of the DotA timer in fractions
    bbox = (
        half_width - offset,
        height // 45,
        half_width + offset,
        height // 30,
    )
    img = np.asarray(ImageGrab.grab(bbox=bbox))  # NOQA
    # Image pre-processing in OpenCV
    # Blend in daytime indicator color into the dark background
    yellow_min = np.array([140, 115, 75], np.uint8)
    yellow_max = np.array([160, 135, 95], np.uint8)
    mask = cv.inRange(img, yellow_min, yellow_max)
    img[mask > 0] = (67, 71, 67)
    img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    return cv.resize(img, None, fx=3, fy=3, interpolation=cv.INTER_CUBIC)


def main(
    to_track: ToTrack = typer.Argument(
        ToTrack.ROSHAN,
        help="Specify the kind of information you want to track. If no argument "
        "is specified, Roshan death time is tracked.",
    ),
    item_or_ability: Optional[str] = typer.Argument(
        None,
        help="Specify the cooldown of what item or ability you want to track. "
        "For abilities, make sure to prefix the hero name "
        "(e.g. `faceless_void_chronosphere`).",
    ),
    language: Language = typer.Option(
        Language.ENGLISH,
        help="Specify the output language for Roshan death timer. If no argument "
        "is specified, English is chosen.",
    ),
    force_update: bool = typer.Option(
        False, "--force_update", help="Force locally stored cache update."
    ),
) -> None:
    """The main function. One can pass a command-line argument to track other
    metrics here."""

    typer.echo("Running...")

    language = [language[:2] if language is not Language.SPANISH else "es"]
    gettext.translation(
        "translate",
        localedir=HOME_DIR / "locale",
        languages=language,
        fallback=True,
    ).install()
    del globals()["_"]

    timers_sep, sep_prefix = TimersSep.ARROW, None
    if to_track in {ToTrack.ROSHAN, ToTrack.GLYPH, ToTrack.BUYBACK}:
        times = to_track.times
        if to_track is ToTrack.ROSHAN:
            sep_prefix = (_("kill"), _("exp"), _("min"), _("max"))
        to_track = _(to_track)
    else:
        cooldown = get_cooldowns(to_track.plural, item_or_ability, force_update)
        to_track = item_or_ability.replace("_", " ")
        if isinstance(cooldown, str | int):
            times = [timedelta(seconds=int(cooldown))]
        else:
            timers_sep = TimersSep.PIPE
            times = [timedelta(seconds=int(delta)) for delta in cooldown]

    reader, screenshot_retries = easyocr.Reader(["en"]), itertools.count(1)

    # Screenshot at most 5 times, and try to OCR screenshot at most 10 times.
    while next(screenshot_retries) < 5:
        image = screenshot_dota_timer()
        ocr_retries = itertools.count(1)
        while not (
            timer := reader.readtext(image, detail=0, allowlist=string.digits + ":")
        ):
            if next(ocr_retries) > 10:
                break
        else:
            break
    else:
        raise ValueError("Too many retries, OCR can't recognize characters.")
    timer = timer[0]
    if ":" not in timer:
        timer = f"{timer[:-2]}:{timer[-2:]}"
    minutes, seconds = map(int, timer.split(":"))
    timer = [timedelta(minutes=minutes, seconds=seconds)]
    times = (
        itertools.accumulate(timer + times)
        if timers_sep is TimersSep.ARROW
        else timer + [timer[0] + delta for delta in times]
    )
    pyperclip.copy(process_timedeltas(times, to_track, timers_sep, sep_prefix))
    typer.secho("Done!", fg=typer.colors.GREEN)


if __name__ == "__main__":
    typer.run(main)
