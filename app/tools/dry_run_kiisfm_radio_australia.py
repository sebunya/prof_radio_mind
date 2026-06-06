"""One-shot dry run for KIIS-FM 106.5 Sydney — radio-australia.org weekly chart collector.

Fetches the static weekly chart from radio-australia.org/kiis-1065.
No data is written to the database.

Note: played_at is synthetic (collection time). Chart covers last 7 days.

robots.txt: PENDING — https://www.radio-australia.org/robots.txt not yet checked.
ToS review: PENDING.

Usage (inside the running app container):
    docker exec rmias-app-1 python -m app.tools.dry_run_kiisfm_radio_australia
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from app.infrastructure.parsers.radio_australia_org import parse_radio_australia_chart

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

_URL = "https://www.radio-australia.org/kiis-1065"
_DUMP_PATH = Path("/tmp/kiisfm_radio_australia_raw.html")


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

    results = parse_radio_australia_chart(response.content, response.status_code)
    logger.info("Parsed %d chart items", len(results))
    for r in results:
        logger.info("  #%d %s — %s", r.rank, r.artist, r.title)

    if not results:
        logger.warning("No chart items — inspect %s", _DUMP_PATH)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
