## { SCRIPT

##
## === DEPENDENCIES
##

## local
from git_helpers import shell_utils

##
## === TESTS
##


def test_defaults():
    config = shell_utils.Config()
    assert config.dry_run is False
    assert config.allow_dirty is False


def test_dry_run_only():
    config = shell_utils.Config(dry_run=True)
    assert config.dry_run is True
    assert config.allow_dirty is False


def test_allow_dirty_only():
    config = shell_utils.Config(allow_dirty=True)
    assert config.dry_run is False
    assert config.allow_dirty is True


def test_both_flags():
    config = shell_utils.Config(dry_run=True, allow_dirty=True)
    assert config.dry_run is True
    assert config.allow_dirty is True


def test_independence():
    ## setting one flag does not affect the other
    config_dry = shell_utils.Config(dry_run=True)
    config_dirty = shell_utils.Config(allow_dirty=True)
    assert config_dry.allow_dirty is False
    assert config_dirty.dry_run is False


## } SCRIPT
