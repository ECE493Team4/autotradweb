#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""pytests for :mod:`.__main__` and :mod:`.common`"""

import argparse
import logging

import pytest

from autotradeweb.__main__ import get_parser, main, log_level


def test_get_parser():
    assert isinstance(get_parser(), argparse.ArgumentParser)


@pytest.mark.parametrize(
    "log_level_string, expected",
    [
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("WARNING", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("CRITICAL", logging.CRITICAL),
    ]
)
def test_log_level(log_level_string, expected):
    assert log_level(log_level_string) == expected


def test_log_level_invalid():
    with pytest.raises(argparse.ArgumentTypeError):
        log_level("nonsuch")


def test_main_missing_key_arg():
    with pytest.raises(SystemExit):
        main()
