#!/usr/bin/env python

"""Tests for `dota_2_rosh_timer` package."""

import unittest
from datetime import timedelta

from dota_2_rosh_timer.dota_2_rosh_timer import (
    TimersSep,
    process_timedeltas,
    timedelta_to_dota_timer,
)


class Dota2RoshTimerUnitTests(unittest.TestCase):
    def test_zero_timedelta(self) -> None:
        self.assertEqual(timedelta_to_dota_timer(timedelta()), "0:00")

    def test_timedelta_less_than_minute(self) -> None:
        self.assertEqual(timedelta_to_dota_timer(timedelta(seconds=30)), "0:30")

    def test_timedelta_one_minute(self) -> None:
        self.assertEqual(timedelta_to_dota_timer(timedelta(minutes=1)), "1:00")

    def test_timedelta_multiple_minutes(self) -> None:
        self.assertEqual(
            timedelta_to_dota_timer(timedelta(minutes=12, seconds=34)), "12:34"
        )

    def test_timedelta_one_hour(self) -> None:
        self.assertEqual(timedelta_to_dota_timer(timedelta(hours=1)), "60:00")

    def test_timedelta_multiple_hours(self) -> None:
        self.assertEqual(
            timedelta_to_dota_timer(timedelta(hours=12, minutes=34, seconds=56)),
            "754:56",
        )

    def test_empty_list(self) -> None:
        self.assertEqual(
            process_timedeltas([], "Roshan", TimersSep.ARROW, None), "Roshan "
        )

    def test_single_delta(self) -> None:
        deltas = [timedelta(minutes=5, seconds=30)]
        expected = "Roshan 5:30"
        self.assertEqual(
            process_timedeltas(deltas, "Roshan", TimersSep.ARROW, None), expected
        )

    def test_multiple_deltas_with_arrow_sep(self) -> None:
        deltas = [timedelta(minutes=5), timedelta(minutes=10), timedelta(minutes=15)]
        expected = "Roshan 5:00 -> 10:00 -> 15:00"
        self.assertEqual(
            process_timedeltas(deltas, "Roshan", TimersSep.ARROW, None), expected
        )

    def test_multiple_deltas_with_pipe_sep(self) -> None:
        deltas = [timedelta(minutes=5), timedelta(minutes=10), timedelta(minutes=15)]
        expected = "Roshan A 5:00 || B 10:00 || C 15:00"
        sep_prefix = ["A", "B", "C"]
        self.assertEqual(
            process_timedeltas(deltas, "Roshan", TimersSep.PIPE, sep_prefix), expected
        )

    def test_none_sep_prefix(self) -> None:
        deltas = [timedelta(minutes=5), timedelta(minutes=10), timedelta(minutes=15)]
        expected = "Roshan  5:00 ||  10:00 ||  15:00"
        sep_prefix = ["", "", ""]
        self.assertEqual(
            process_timedeltas(deltas, "Roshan", TimersSep.PIPE, sep_prefix), expected
        )


if __name__ == "__main__":
    Dota2RoshTimerUnitTests.main()
