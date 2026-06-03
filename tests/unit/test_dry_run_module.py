"""Tests that app.tools.dry_run_capital can be imported and that __main__ entrypoint exists."""

from __future__ import annotations


def test_dry_run_module_importable() -> None:
    import app.tools.dry_run_capital as mod

    assert hasattr(mod, "run_dry_run")
    assert hasattr(mod, "main")
    assert callable(mod.run_dry_run)
    assert callable(mod.main)


def test_dry_run_module_has_correct_uuids() -> None:
    import uuid

    from app.tools.dry_run_capital import _CAPITAL_SOURCE_ID, _CAPITAL_STATION_ID

    ns = uuid.NAMESPACE_DNS
    assert _CAPITAL_STATION_ID == uuid.uuid5(ns, "station.CAPITALFM")
    assert _CAPITAL_SOURCE_ID == uuid.uuid5(ns, "source.CAPITALFM.online_radio_box")


def test_scripts_dry_run_delegates_to_module() -> None:
    """The scripts/ wrapper must import from app.tools, not duplicate logic."""
    import ast
    from pathlib import Path

    script = Path("scripts/dry_run_capital.py").read_text()
    tree = ast.parse(script)
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    # Verify it imports from app.tools.dry_run_capital
    module_names = [
        getattr(node, "module", "") or ""
        for node in imports
        if isinstance(node, ast.ImportFrom)
    ]
    assert any("app.tools.dry_run_capital" in m for m in module_names), (
        "scripts/dry_run_capital.py must import from app.tools.dry_run_capital"
    )
