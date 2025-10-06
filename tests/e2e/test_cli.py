"""End-to-end CLI tests."""
from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("structlog")

from cli.aj import build_parser


def test_cli_help(capsys: Any) -> None:
    """Parser should render help when no command is provided."""

    parser = build_parser()
    parser.parse_args([])
    parser.print_help()
    captured = capsys.readouterr()
    assert "bootstrap" in captured.out
    assert "ingest" in captured.out
