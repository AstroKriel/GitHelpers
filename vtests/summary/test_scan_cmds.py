## { V-TEST

##
## === DEPENDENCIES
##

## stdlib
from pathlib import Path

## third-party
import pytest

## local
from git_helpers import shell_interface
from git_helpers.summary import git_scan
from vtests.helpers import git, make_commit
from vtests.summary.conftest import add_submodule, make_bare_remote, make_repo_at, set_submodule_ignore_all

##
## === HELPERS
##

_CONFIG = shell_interface.Config()


##
## === DISCOVERY
##


class TestFindRepos_Discovery:

    def test_finds_repo_at_depth_1(
        self,
        scan_root: Path,
    ) -> None:
        make_repo_at(scan_root / "proj")
        repos = git_scan._find_repos(root=scan_root, max_depth=1)
        assert repos == [scan_root / "proj"]

    def test_finds_repo_nested_at_depth_2(
        self,
        scan_root: Path,
    ) -> None:
        make_repo_at(scan_root / "group" / "proj")
        repos = git_scan._find_repos(root=scan_root, max_depth=2)
        assert repos == [scan_root / "group" / "proj"]

    def test_does_not_find_beyond_max_depth(
        self,
        scan_root: Path,
    ) -> None:
        make_repo_at(scan_root / "group" / "proj")
        repos = git_scan._find_repos(root=scan_root, max_depth=1)
        assert repos == []

    def test_does_not_descend_into_repo(
        self,
        scan_root: Path,
    ) -> None:
        parent = make_repo_at(scan_root / "outer")
        make_repo_at(parent / "inner")
        repos = git_scan._find_repos(root=scan_root, max_depth=3)
        assert repos == [scan_root / "outer"]

    def test_finds_multiple_sibling_repos(
        self,
        scan_root: Path,
    ) -> None:
        make_repo_at(scan_root / "a")
        make_repo_at(scan_root / "b")
        repos = git_scan._find_repos(root=scan_root, max_depth=1)
        assert repos == [scan_root / "a", scan_root / "b"]

    def test_returns_empty_when_no_repos(
        self,
        scan_root: Path,
    ) -> None:
        (scan_root / "empty").mkdir()
        repos = git_scan._find_repos(root=scan_root, max_depth=2)
        assert repos == []


##
## === SUBMODULE PARSING
##


class TestActiveSubmodulePaths_Parsing:

    def test_returns_empty_when_no_gitmodules(
        self,
        tmp_path: Path,
    ) -> None:
        paths = git_scan._active_submodule_paths(tmp_path)
        assert paths == []

    def test_returns_path_for_active_submodule(
        self,
        tmp_path: Path,
    ) -> None:
        (tmp_path / ".gitmodules").write_text(
            '[submodule "sub"]\n\tpath = sub\n\turl = https://example.com/sub.git\n'
        )
        paths = git_scan._active_submodule_paths(tmp_path)
        assert paths == [tmp_path / "sub"]

    def test_skips_submodule_with_ignore_all(
        self,
        tmp_path: Path,
    ) -> None:
        (tmp_path / ".gitmodules").write_text(
            '[submodule "sub"]\n\tpath = sub\n\turl = https://example.com/sub.git\n\tignore = all\n'
        )
        paths = git_scan._active_submodule_paths(tmp_path)
        assert paths == []

    def test_returns_only_active_when_mixed(
        self,
        tmp_path: Path,
    ) -> None:
        (tmp_path / ".gitmodules").write_text(
            '[submodule "active"]\n\tpath = active\n\turl = https://example.com/a.git\n'
            '[submodule "passive"]\n\tpath = passive\n\turl = https://example.com/p.git\n\tignore = all\n'
        )
        paths = git_scan._active_submodule_paths(tmp_path)
        assert paths == [tmp_path / "active"]


##
## === SUBMODULE RECURSION
##


class TestFindRepos_SubmoduleRecursion:

    def test_finds_submodule_with_git_file(
        self,
        scan_root: Path,
        tmp_path: Path,
    ) -> None:
        parent = make_repo_at(scan_root / "parent")
        sub_source = make_repo_at(tmp_path / "sub_source")
        add_submodule(parent, sub_source, "sub")
        repos = git_scan._find_repos(root=scan_root, max_depth=1)
        assert scan_root / "parent" / "sub" in repos

    def test_recurses_into_active_submodule(
        self,
        scan_root: Path,
        tmp_path: Path,
    ) -> None:
        parent = make_repo_at(scan_root / "parent")
        sub_source = make_repo_at(tmp_path / "sub_source")
        add_submodule(parent, sub_source, "active")
        repos = git_scan._find_repos(root=scan_root, max_depth=1)
        assert scan_root / "parent" in repos
        assert scan_root / "parent" / "active" in repos

    def test_does_not_recurse_into_ignored_submodule(
        self,
        scan_root: Path,
        tmp_path: Path,
    ) -> None:
        parent = make_repo_at(scan_root / "parent")
        sub_source = make_repo_at(tmp_path / "sub_source")
        add_submodule(parent, sub_source, "passive")
        set_submodule_ignore_all(parent, "passive")
        repos = git_scan._find_repos(root=scan_root, max_depth=1)
        assert scan_root / "parent" / "passive" not in repos


##
## === REPO STATUS
##


class TestGetRepoStatus_DirtyFiles:

    def test_clean_repo_has_zero_dirty_files(
        self,
        scan_root: Path,
    ) -> None:
        repo = make_repo_at(scan_root / "proj")
        status = git_scan._get_repo_status(path=repo, is_fetching=False)
        assert status.dirty_files == 0

    def test_dirty_repo_counts_modified_files(
        self,
        scan_root: Path,
    ) -> None:
        repo = make_repo_at(scan_root / "proj")
        (repo / "dirty.txt").write_text("changes")
        status = git_scan._get_repo_status(path=repo, is_fetching=False)
        assert status.dirty_files == 1


class TestGetRepoStatus_Diverged:

    def test_no_upstream_means_no_divergence(
        self,
        scan_root: Path,
    ) -> None:
        repo = make_repo_at(scan_root / "proj")
        status = git_scan._get_repo_status(path=repo, is_fetching=False)
        assert status.diverged == []

    def test_detects_commits_ahead_of_upstream(
        self,
        scan_root: Path,
        tmp_path: Path,
    ) -> None:
        remote = make_bare_remote(tmp_path / "remote.git")
        repo = make_repo_at(scan_root / "proj")
        git(["remote", "add", "origin", str(remote)], cwd=repo)
        git(["push", "-u", "origin", "main"], cwd=repo)
        make_commit(repo, msg="extra")
        status = git_scan._get_repo_status(path=repo, is_fetching=False)
        assert len(status.diverged) == 1
        assert status.diverged[0].name == "main"
        assert status.diverged[0].commits_ahead == 1
        assert status.diverged[0].commits_behind == 0

    def test_detects_commits_behind_upstream(
        self,
        scan_root: Path,
        tmp_path: Path,
    ) -> None:
        remote = make_bare_remote(tmp_path / "remote.git")
        repo = make_repo_at(scan_root / "proj")
        git(["remote", "add", "origin", str(remote)], cwd=repo)
        git(["push", "-u", "origin", "main"], cwd=repo)
        ## a second clone pushes a new commit to the remote
        other = tmp_path / "other"
        git(["clone", str(remote), str(other)], cwd=tmp_path)
        for key, val in {"user.name": "Test", "user.email": "t@t.com"}.items():
            git(["config", key, val], cwd=other)
        make_commit(other, msg="remote commit")
        git(["push"], cwd=other)
        ## repo fetches and now sees it is behind
        status = git_scan._get_repo_status(path=repo, is_fetching=True)
        assert len(status.diverged) == 1
        assert status.diverged[0].name == "main"
        assert status.diverged[0].commits_ahead == 0
        assert status.diverged[0].commits_behind == 1

    def test_pushed_repo_has_no_divergence(
        self,
        scan_root: Path,
        tmp_path: Path,
    ) -> None:
        remote = make_bare_remote(tmp_path / "remote.git")
        repo = make_repo_at(scan_root / "proj")
        git(["remote", "add", "origin", str(remote)], cwd=repo)
        git(["push", "-u", "origin", "main"], cwd=repo)
        status = git_scan._get_repo_status(path=repo, is_fetching=False)
        assert status.diverged == []


class TestGetRepoStatus_CommitsInWindow:

    def test_zero_when_since_not_given(
        self,
        scan_root: Path,
    ) -> None:
        repo = make_repo_at(scan_root / "proj")
        status = git_scan._get_repo_status(path=repo, is_fetching=False)
        assert status.commits_in_window == 0

    def test_counts_recent_commits_within_window(
        self,
        scan_root: Path,
    ) -> None:
        repo = make_repo_at(scan_root / "proj")
        make_commit(repo, msg="second")
        status = git_scan._get_repo_status(path=repo, is_fetching=False, since=1)
        assert status.commits_in_window == 2


class TestGetRepoStatus_LastCommit:

    def test_repo_with_commit_has_finite_age(
        self,
        scan_root: Path,
    ) -> None:
        repo = make_repo_at(scan_root / "proj")
        status = git_scan._get_repo_status(path=repo, is_fetching=False)
        assert status.last_commit_age_days < 1
        assert status.last_commit_rel != "(no commits)"


##
## === COMMAND OUTPUT
##


class TestScanRepos_Output:

    def test_no_repos_found_outcome(
        self,
        scan_root: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        (scan_root / "empty").mkdir()
        git_scan.scan_repos(_CONFIG, depth=1, is_fetch_skipped=True)
        captured = capsys.readouterr()
        assert "no git repos found" in captured.err

    def test_all_clean_shows_synced_outcome(
        self,
        scan_root: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        remote = make_bare_remote(tmp_path / "remote.git")
        repo = make_repo_at(scan_root / "proj")
        git(["remote", "add", "origin", str(remote)], cwd=repo)
        git(["push", "-u", "origin", "main"], cwd=repo)
        git_scan.scan_repos(_CONFIG, depth=1, is_fetch_skipped=True)
        captured = capsys.readouterr()
        assert "all repos are clean and synced" in captured.err

    def test_dirty_repo_shown_in_output(
        self,
        scan_root: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        repo = make_repo_at(scan_root / "proj")
        (repo / "dirty.txt").write_text("changes")
        git_scan.scan_repos(_CONFIG, depth=1, is_fetch_skipped=True)
        captured = capsys.readouterr()
        assert "proj" in captured.err
        assert "dirty" in captured.err

    def test_unpushed_repo_shown_in_output(
        self,
        scan_root: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        remote = make_bare_remote(tmp_path / "remote.git")
        repo = make_repo_at(scan_root / "proj")
        git(["remote", "add", "origin", str(remote)], cwd=repo)
        git(["push", "-u", "origin", "main"], cwd=repo)
        make_commit(repo, msg="extra")
        git_scan.scan_repos(_CONFIG, depth=1, is_fetch_skipped=True)
        captured = capsys.readouterr()
        assert "proj" in captured.err
        assert "unpushed" in captured.err

    def test_unpulled_repo_shown_in_output(
        self,
        scan_root: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        remote = make_bare_remote(tmp_path / "remote.git")
        repo = make_repo_at(scan_root / "proj")
        git(["remote", "add", "origin", str(remote)], cwd=repo)
        git(["push", "-u", "origin", "main"], cwd=repo)
        other = tmp_path / "other"
        git(["clone", str(remote), str(other)], cwd=tmp_path)
        for key, val in {"user.name": "Test", "user.email": "t@t.com"}.items():
            git(["config", key, val], cwd=other)
        make_commit(other, msg="remote commit")
        git(["push"], cwd=other)
        git_scan.scan_repos(_CONFIG, depth=1, is_fetch_skipped=True)
        ## without fetch, behind count is stale: repo must fetch first to see it
        git_scan._fetch(repo)
        capsys.readouterr()
        git_scan.scan_repos(_CONFIG, depth=1, is_fetch_skipped=True)
        captured = capsys.readouterr()
        assert "unpulled" in captured.err

    def test_since_shows_recently_active_repos(
        self,
        scan_root: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        remote = make_bare_remote(tmp_path / "remote.git")
        repo = make_repo_at(scan_root / "proj")
        git(["remote", "add", "origin", str(remote)], cwd=repo)
        git(["push", "-u", "origin", "main"], cwd=repo)
        git_scan.scan_repos(_CONFIG, depth=1, since=1, is_fetch_skipped=True)
        captured = capsys.readouterr()
        assert "proj" in captured.err

    def test_summary_line_shows_repo_counts(
        self,
        scan_root: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        repo = make_repo_at(scan_root / "proj")
        (repo / "dirty.txt").write_text("changes")
        git_scan.scan_repos(_CONFIG, depth=1, is_fetch_skipped=True)
        captured = capsys.readouterr()
        assert "repos scanned" in captured.err
        assert "dirty" in captured.err

    def test_summary_includes_unpulled_count(
        self,
        scan_root: Path,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        remote = make_bare_remote(tmp_path / "remote.git")
        repo = make_repo_at(scan_root / "proj")
        git(["remote", "add", "origin", str(remote)], cwd=repo)
        git(["push", "-u", "origin", "main"], cwd=repo)
        other = tmp_path / "other"
        git(["clone", str(remote), str(other)], cwd=tmp_path)
        for key, val in {"user.name": "Test", "user.email": "t@t.com"}.items():
            git(["config", key, val], cwd=other)
        make_commit(other, msg="remote commit")
        git(["push"], cwd=other)
        git_scan.scan_repos(_CONFIG, depth=1, is_fetch_skipped=False)
        captured = capsys.readouterr()
        assert "with unpulled commits" in captured.err

    def test_since_shows_commit_count_in_output(
        self,
        scan_root: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        make_repo_at(scan_root / "proj")
        git_scan.scan_repos(_CONFIG, depth=1, since=1, is_fetch_skipped=True)
        captured = capsys.readouterr()
        assert "commits" in captured.err

    def test_shows_repo_relative_path(
        self,
        scan_root: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        repo = make_repo_at(scan_root / "group" / "myproject")
        (repo / "dirty.txt").write_text("changes")
        git_scan.scan_repos(_CONFIG, depth=2, is_fetch_skipped=True)
        captured = capsys.readouterr()
        assert "group/myproject" in captured.err


## } V-TEST
