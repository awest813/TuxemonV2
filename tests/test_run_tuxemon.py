# SPDX-License-Identifier: GPL-3.0
from argparse import Namespace

from run_tuxemon import apply_config_from_args


class DummyConfig:
    def __init__(self):
        self.mods = []
        self.skip_titlescreen = False
        self.splash = True


def test_apply_config_from_args_sets_test_map_and_startup_flags():
    config = DummyConfig()
    args = Namespace(mod=None, test_map="debug_map.tmx")

    apply_config_from_args(config, args)

    assert config.test_map == "debug_map.tmx"
    assert config.skip_titlescreen is True
    assert config.splash is False


def test_apply_config_from_args_inserts_mod_when_provided():
    config = DummyConfig()
    config.mods = ["coremod"]
    args = Namespace(mod="custom_mod", test_map=None)

    apply_config_from_args(config, args)

    assert config.mods == ["custom_mod", "coremod"]
