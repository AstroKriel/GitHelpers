## { U-TEST

##
## === DEPENDENCIES
##

## stdlib
import unittest

## local
from git_helpers import shell_interface

##
## === TEST SUITE
##


class TestConfig_Defaults(unittest.TestCase):

    def test_dry_run_is_false(
        self,
    ) -> None:
        config = shell_interface.Config()
        self.assertFalse(
            config.dry_run,
        )

    def test_allow_dirty_is_false(
        self,
    ) -> None:
        config = shell_interface.Config()
        self.assertFalse(
            config.allow_dirty,
        )


class TestConfig_Flags(unittest.TestCase):

    def test_dry_run_flag(
        self,
    ) -> None:
        config = shell_interface.Config(dry_run=True)
        self.assertTrue(
            config.dry_run,
        )
        self.assertFalse(
            config.allow_dirty,
        )

    def test_allow_dirty_flag(
        self,
    ) -> None:
        config = shell_interface.Config(allow_dirty=True)
        self.assertFalse(
            config.dry_run,
        )
        self.assertTrue(
            config.allow_dirty,
        )

    def test_both_flags(
        self,
    ) -> None:
        config = shell_interface.Config(dry_run=True, allow_dirty=True)
        self.assertTrue(
            config.dry_run,
        )
        self.assertTrue(
            config.allow_dirty,
        )

    def test_flags_are_independent(
        self,
    ) -> None:
        config_dry = shell_interface.Config(dry_run=True)
        config_dirty = shell_interface.Config(allow_dirty=True)
        self.assertFalse(
            config_dry.allow_dirty,
        )
        self.assertFalse(
            config_dirty.dry_run,
        )


##
## === ENTRY POINT
##

if __name__ == "__main__":
    _ = unittest.main()

## } U-TEST
