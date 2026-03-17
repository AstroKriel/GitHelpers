"""
Unit tests for the Config dataclass.
"""

##
## === DEPENDENCIES
##

## local
from git_helpers.shell_utils import Config

##
## === TESTS
##


def test_defaults():
    config = Config()
    assert config.dry_run is False
    assert config.allow_dirty is False


def test_dry_run_only():
    config = Config(dry_run=True)
    assert config.dry_run is True
    assert config.allow_dirty is False


def test_allow_dirty_only():
    config = Config(allow_dirty=True)
    assert config.dry_run is False
    assert config.allow_dirty is True


def test_both_flags():
    config = Config(dry_run=True, allow_dirty=True)
    assert config.dry_run is True
    assert config.allow_dirty is True


def test_independence():
    ## setting one flag does not affect the other
    config_dry = Config(dry_run=True)
    config_dirty = Config(allow_dirty=True)
    assert config_dry.allow_dirty is False
    assert config_dirty.dry_run is False
