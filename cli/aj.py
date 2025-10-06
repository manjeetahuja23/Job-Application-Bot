"""Command-line interface for autojob-bot."""
from __future__ import annotations

import argparse
import sys
from typing import Any

import structlog

from app.core.logging import configure_logging
from app.db.session import session_scope
from app.ingestion.greenhouse import GreenhouseIngestion
from app.ingestion.lever import LeverIngestion
from app.ingestion.workday_public import WorkdayIngestion

LOGGER = structlog.get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI commands."""

    parser = argparse.ArgumentParser(prog="aj")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("bootstrap", help="Seed default jobs")

    render_docs = subparsers.add_parser("render", help="Render documents")
    render_docs.add_argument("--role", required=False, default="Automation Engineer")
    render_docs.add_argument("--company", required=False, default="Example Corp")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest job postings from a source")
    ingest_subparsers = ingest_parser.add_subparsers(dest="source", required=True)

    def add_common_arguments(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--limit", type=int, default=None, help="Max jobs to process")
        subparser.add_argument("--dry-run", action="store_true", help="Process without saving")

    greenhouse_parser = ingest_subparsers.add_parser(
        "greenhouse", help="Ingest from a Greenhouse job board"
    )
    greenhouse_parser.add_argument("--board", required=True, help="Greenhouse board URL")
    add_common_arguments(greenhouse_parser)

    lever_parser = ingest_subparsers.add_parser("lever", help="Ingest from a Lever board")
    lever_parser.add_argument("--company", required=True, help="Lever company handle")
    add_common_arguments(lever_parser)

    workday_parser = ingest_subparsers.add_parser(
        "workday", help="Ingest from a Workday public JSON endpoint"
    )
    workday_parser.add_argument("--url", required=True, help="Workday search URL")
    add_common_arguments(workday_parser)

    return parser


def _handle_render(role: str, company: str) -> None:
    from app.docs import tailor

    resume = tailor.build_resume({"role": role, "company": company})
    cover = tailor.build_cover_letter({"role": role, "company": company})
    print("RESUME:\n" + resume)
    print("\nCOVER LETTER:\n" + cover)


def _resolve_ingestor(args: argparse.Namespace) -> Any:
    if args.source == "greenhouse":
        return GreenhouseIngestion(board_url=args.board)
    if args.source == "lever":
        return LeverIngestion(company=args.company)
    if args.source == "workday":
        return WorkdayIngestion(search_url=args.url)
    raise ValueError(f"Unsupported ingestion source: {args.source}")


def _handle_ingest(args: argparse.Namespace) -> None:
    ingestor = _resolve_ingestor(args)
    LOGGER.info("ingest.start", source=ingestor.source, limit=args.limit, dry_run=args.dry_run)
    with session_scope() as session:
        result = ingestor.ingest(session, limit=args.limit, dry_run=args.dry_run)
    LOGGER.info("ingest.complete", **result.as_dict())


def main(args: list[str] | None = None) -> None:
    """CLI entry point."""

    configure_logging()
    parser = build_parser()
    namespace = parser.parse_args(args=args)

    if namespace.command == "bootstrap":
        from app.tasks import jobs

        jobs.bootstrap_defaults()
    elif namespace.command == "render":
        _handle_render(namespace.role, namespace.company)
    elif namespace.command == "ingest":
        _handle_ingest(namespace)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
