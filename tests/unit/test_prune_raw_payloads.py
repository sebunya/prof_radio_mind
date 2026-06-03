"""Tests for the raw payload retention/prune tool."""

from __future__ import annotations

import os
import time
from pathlib import Path

from app.tools.prune_raw_payloads import prune


def _make_file(path: Path, age_days: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"payload")
    old = time.time() - age_days * 86400
    os.utime(path, (old, old))


def test_retention_disabled_is_noop(tmp_path: Path) -> None:
    _make_file(tmp_path / "2026/01/01/old.bin", age_days=100)
    deleted, freed = prune(str(tmp_path), retention_days=0)
    assert deleted == 0
    assert freed == 0
    assert (tmp_path / "2026/01/01/old.bin").exists()


def test_missing_root_is_noop(tmp_path: Path) -> None:
    deleted, freed = prune(str(tmp_path / "does_not_exist"), retention_days=30)
    assert deleted == 0
    assert freed == 0


def test_old_files_pruned_recent_kept(tmp_path: Path) -> None:
    _make_file(tmp_path / "2026/01/01/old.bin", age_days=40)
    _make_file(tmp_path / "2026/06/01/recent.bin", age_days=2)

    deleted, freed = prune(str(tmp_path), retention_days=30)

    assert deleted == 1
    assert freed == len(b"payload")
    assert not (tmp_path / "2026/01/01/old.bin").exists()
    assert (tmp_path / "2026/06/01/recent.bin").exists()


def test_empty_dirs_removed_after_prune(tmp_path: Path) -> None:
    _make_file(tmp_path / "2026/01/01/old.bin", age_days=40)
    prune(str(tmp_path), retention_days=30)
    # The now-empty date dirs should be cleaned up.
    assert not (tmp_path / "2026/01/01").exists()


def test_boundary_file_just_under_retention_kept(tmp_path: Path) -> None:
    _make_file(tmp_path / "a/b/c.bin", age_days=29)
    deleted, _ = prune(str(tmp_path), retention_days=30)
    assert deleted == 0
    assert (tmp_path / "a/b/c.bin").exists()
