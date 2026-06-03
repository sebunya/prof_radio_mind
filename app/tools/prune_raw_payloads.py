"""Prune raw payload files older than the configured retention window.

Raw payloads are stored under settings.raw_payload_storage_path in
date-bucketed subdirectories (YYYY/MM/DD/<run_id>.bin). Without pruning the
volume grows unbounded. This tool deletes files whose modification time is
older than RAW_PAYLOAD_RETENTION_DAYS and removes the now-empty date dirs.

Safety:
- Does nothing when RAW_PAYLOAD_RETENTION_DAYS <= 0 (the default).
- Only operates on the configured storage root.
- Never touches the database — raw_payloads rows are kept as an audit trail;
  only the on-disk blobs are pruned.

Usage (inside the running app container):
    docker exec rmias-app-1 python -m app.tools.prune_raw_payloads

Recommended cron (on the host) once retention is set:
    0 4 * * *  docker exec rmias-app-1 python -m app.tools.prune_raw_payloads
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from app.core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("prune_raw_payloads")


def prune(storage_root: str, retention_days: int) -> tuple[int, int]:
    """Delete files older than retention_days. Returns (files_deleted, bytes_freed)."""
    if retention_days <= 0:
        logger.info("Retention disabled (RAW_PAYLOAD_RETENTION_DAYS=%d); nothing to do.",
                    retention_days)
        return 0, 0

    root = Path(storage_root)
    if not root.exists():
        logger.info("Storage root %s does not exist; nothing to prune.", storage_root)
        return 0, 0

    cutoff = time.time() - retention_days * 86400
    files_deleted = 0
    bytes_freed = 0

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            if path.stat().st_mtime < cutoff:
                size = path.stat().st_size
                path.unlink()
                files_deleted += 1
                bytes_freed += size
        except OSError as exc:
            logger.warning("Failed to remove %s: %s", path, exc)

    # Remove now-empty date directories (deepest first).
    for path in sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir():
            try:
                next(path.iterdir())
            except StopIteration:
                try:
                    path.rmdir()
                except OSError:
                    pass

    logger.info(
        "Pruned %d file(s), freed %.2f MB (retention=%d days, root=%s)",
        files_deleted,
        bytes_freed / (1024 * 1024),
        retention_days,
        storage_root,
    )
    return files_deleted, bytes_freed


def main() -> None:
    prune(settings.raw_payload_storage_path, settings.raw_payload_retention_days)


if __name__ == "__main__":
    main()
