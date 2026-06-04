from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from app.core.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("scripts.enrich_catalog")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manual Spotify catalog metadata enrichment utility."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of songs to fetch and process per database transaction.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum total number of songs to enrich in this run.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="respectful delay in seconds sleep between Spotify search API calls.",
    )
    args = parser.parse_args()

    # Pre-flight check
    if not settings.spotify_client_id or not settings.spotify_client_secret:
        logger.error(
            "Spotify integration is not configured. "
            "Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET."
        )
        sys.exit(1)

    from app.application.spotify.enricher import enrich_songs_batch
    from app.infrastructure.database.session import _get_factory as _factory

    session_factory = _factory()
    total_enriched = 0
    limit = args.limit

    logger.info(
        "Starting manual enrichment: limit=%d batch_size=%d delay=%.2fs",
        limit,
        args.batch_size,
        args.delay,
    )

    while total_enriched < limit:
        remaining = limit - total_enriched
        batch = min(args.batch_size, remaining)

        try:
            async with session_factory() as session:
                count = await enrich_songs_batch(
                    session, batch_size=batch, delay_seconds=args.delay
                )
                if count == 0:
                    logger.info("No more pending songs found in database.")
                    break
                total_enriched += count
                logger.info(
                    "Batch complete: processed %d songs. Total: %d",
                    count,
                    total_enriched,
                )
        except Exception as e:
            logger.error("Enrichment batch run encountered a critical error: %s", e)
            sys.exit(1)

    logger.info(
        "Catalog enrichment complete. Total songs processed: %d", total_enriched
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Enrichment run interrupted by user.")
        sys.exit(0)
