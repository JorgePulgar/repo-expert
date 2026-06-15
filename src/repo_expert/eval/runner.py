"""Eval runner: run both metrics and write a markdown + JSON report."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from repo_expert.config.instance import get_instance_config
from repo_expert.eval.groundedness import run_groundedness
from repo_expert.eval.relevance import run_relevance


def run_eval(instance: str | None = None) -> dict:
    """Run relevance + groundedness for an instance and return a combined report."""
    cfg = get_instance_config(instance)
    return {
        "instance": cfg.name,
        "repo": cfg.primary_repo.slug,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "relevance": run_relevance(cfg.name),
        "groundedness": run_groundedness(cfg.name),
    }


def _to_markdown(report: dict) -> str:
    rel = report["relevance"]
    gnd = report["groundedness"]
    by_kind = " · ".join(f"{k}={v}" for k, v in rel["relevance_by_kind"].items())
    lines = [
        f"# Evaluation — {report['instance']} ({report['repo']})",
        "",
        f"_Generated {report['generated_at']} · n={rel['n']} questions_",
        "",
        "## Retrieval",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Routing accuracy | {rel['routing_accuracy']} |",
        f"| Relevance hit@{rel['top_k']} | {rel['relevance_hit_at_k']} |",
        f"| Relevance by kind | {by_kind} |",
        "",
        "## Groundedness",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Faithfulness rate (judge) | {gnd['faithfulness_rate']} |",
        f"| Mean faithfulness score | {gnd['mean_faithfulness_score']} |",
        f"| Agent self-grounded rate | {gnd['self_grounded_rate']} |",
        "",
    ]
    return "\n".join(lines)


def write_report(
    report: dict,
    md_path: str | Path = "docs/eval-results.md",
    json_path: str | Path = "docs/eval-results.json",
) -> tuple[Path, Path]:
    """Write the markdown summary and full JSON report; return their paths."""
    md, js = Path(md_path), Path(json_path)
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(_to_markdown(report), encoding="utf-8")
    js.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return md, js
