"""Backwards-compatible entry point for the Capital FM UK one-shot dry run.

Prefer the module form inside the container:
    docker exec rmias-app-1 python -m app.tools.dry_run_capital

This script remains here for operators who run it directly from the
cloned repo outside a container (e.g. local development).
"""

from app.tools.dry_run_capital import main

if __name__ == "__main__":
    main()
