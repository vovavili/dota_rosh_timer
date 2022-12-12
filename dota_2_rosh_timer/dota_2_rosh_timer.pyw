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
import string
import tkinter as tk
from collections.abc import Iterable
from datetime import timedelta
from enum import Enum
from gettext import gettext as _
from typing import Literal, Optional

import easyocr
import numpy as np
import numpy.typing as npt
import pyperclip
import screeninfo
import typer
from cv2 import cv2 as cv
from PIL import ImageGrab

from cache import HOME_DIR, get_cooldowns


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
    image = np.asarray(ImageGrab.grab(bbox=bbox))  # NOQA
    # Image pre-processing in OpenCV
    # Blend in daytime indicator color into the dark background
    yellow_min = np.array([140, 115, 75], np.uint8)
    yellow_max = np.array([160, 135, 95], np.uint8)
    mask = cv.inRange(image, yellow_min, yellow_max)
    image[mask > 0] = (67, 71, 67)
    image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    return cv.resize(image, None, fx=3, fy=3, interpolation=cv.INTER_CUBIC)


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
    del globals()["_"]  # Keep PyCharm happy

    timers_sep, sep_prefix = TimersSep.ARROW, None
    if to_track in {ToTrack.ROSHAN, ToTrack.GLYPH, ToTrack.BUYBACK}:
        times = to_track.times
        if to_track is ToTrack.ROSHAN:
            sep_prefix = (_("kill"), _("exp"), _("min"), _("max"))
        to_track = _(to_track)
    else:
        cooldown = get_cooldowns(to_track.plural, item_or_ability, force_update)
        if isinstance(cooldown, str | int):
            times = [timedelta(seconds=int(cooldown))]
        else:
            timers_sep = TimersSep.PIPE
            times = [timedelta(seconds=int(delta)) for delta in cooldown]
            if to_track is to_track.ABILITY and len(times) == 3:
                sep_prefix = ("lvl 6", "lvl 12", "lvl 18")
        to_track = item_or_ability.replace("_", " ")

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
        pyperclip.copy("")
        # Make a bell sound to indicate an OCR error
        root = tk.Tk()
        root.overrideredirect(True)
        root.withdraw()
        root.bell()
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
