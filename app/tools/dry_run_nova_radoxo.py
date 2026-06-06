"""One-shot dry run for Nova 96.9 — radoxo.com playlist collector.

Fetches https://radoxo.com/australia/nova-969/playlist and parses the
full day's playlist. No data is written to the database.

Parser confirmed on real HTML 2026-06-06:
  li.playlist-track > span[data-ts] → exact Unix broadcast timestamp
  span.playlist-track__song / span.playlist-track__artist

robots.txt: PENDING — https://radoxo.com/robots.txt not yet checked.
ToS review: PENDING.

Usage (inside the running app container):
    docker exec rmias-app-1 python -m app.tools.dry_run_nova_radoxo
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from app.infrastructure.parsers.radoxo import parse_radoxo_playlist

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

_URL = "https://radoxo.com/australia/nova-969/playlist"
_DUMP_PATH = Path("/tmp/nova_radoxo_raw.html")


async def main() -> int:
    from app.infrastructure.http.client import build_client

    logger.info("Fetching %s", _URL)
    async with await build_client(timeout=30.0) as client:
        response = await client.get(_URL)

    logger.info("HTTP %d content-type=%s bytes=%d",
                response.status_code,
                response.headers.get("content-type", "?"),
                len(response.content))

    _DUMP_PATH.write_bytes(response.content)
    logger.info("Raw HTML saved to %s", _DUMP_PATH)

    results = parse_radoxo_playlist(response.content, response.status_code)
    logger.info("Parsed %d tracks", len(results))
    for r in results[:10]:
        logger.info("  %s  %s — %s  [%s]",
                    r.played_at.strftime("%H:%M:%S UTC"),
                    r.artist, r.title, r.source_event_id)
    if len(results) > 10:
        logger.info("  ... and %d more", len(results) - 10)

    if not results:
        logger.warning("No tracks parsed — inspect %s", _DUMP_PATH)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
