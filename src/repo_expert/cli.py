"""Command-line entrypoint for Repo Expert (``repo-expert ...``)."""

from __future__ import annotations

import argparse
import logging

from repo_expert.config.instance import get_instance_config


def _cmd_ingest(args: argparse.Namespace) -> None:
    from repo_expert.ingestion.pipeline import ingest

    cfg = get_instance_config(args.instance)
    summary = ingest(cfg)
    print("Ingestion complete:")
    for index, count in summary.items():
        print(f"  {index}: {count} chunks")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repo-expert", description="Agentic RAG over a repo.")
    parser.add_argument(
        "--instance", default=None, help="Instance to target (default: REPO_EXPERT_INSTANCE)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_p = sub.add_parser("ingest", help="Fetch, chunk, embed, index, and (re)build the KB.")
    ingest_p.set_defaults(func=_cmd_ingest)

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
