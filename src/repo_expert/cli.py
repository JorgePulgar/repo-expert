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


def _cmd_eval(args: argparse.Namespace) -> None:
    from repo_expert.eval.runner import run_eval, write_report

    report = run_eval(args.instance)
    md, js = write_report(report)
    rel, gnd = report["relevance"], report["groundedness"]
    print(f"Eval complete ({report['instance']}, n={rel['n']}):")
    print(f"  routing accuracy      : {rel['routing_accuracy']}")
    print(f"  relevance hit@{rel['top_k']}       : {rel['relevance_hit_at_k']}")
    print(f"  faithfulness rate     : {gnd['faithfulness_rate']}")
    print(f"  mean faithfulness     : {gnd['mean_faithfulness_score']}")
    print(f"  report: {md} | {js}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="repo-expert", description="Agentic RAG over a repo.")
    parser.add_argument(
        "--instance", default=None, help="Instance to target (default: REPO_EXPERT_INSTANCE)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_p = sub.add_parser("ingest", help="Fetch, chunk, embed, index, and (re)build the KB.")
    ingest_p.set_defaults(func=_cmd_ingest)

    eval_p = sub.add_parser("eval", help="Run retrieval + groundedness eval and write a report.")
    eval_p.set_defaults(func=_cmd_eval)

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
