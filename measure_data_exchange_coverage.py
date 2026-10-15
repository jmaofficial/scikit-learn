#!/usr/bin/env python3
"""
Metric 1: Data exchange coverage

Run this from the root of the scikit-learn repository, in an environment
that imports the scikit-learn version/commit you want to measure.

The script reports:
1) set_output coverage among transformer-like estimators
2) Array API support among all instantiated estimators
3) a transparent combined capability-pair coverage score

It writes:
- data_exchange_coverage.csv
- data_exchange_coverage_summary.txt
"""

from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import os

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", ROOT / "results"))
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

import sklearn

try:
    from sklearn.utils.discovery import all_estimators
except ImportError:
    from sklearn.utils import all_estimators

from sklearn.utils import get_tags


def git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def safe_callable(obj, name: str) -> bool:
    try:
        return callable(getattr(obj, name))
    except Exception:
        return False


def main() -> None:
    rows = []
    skipped = []

    for name, cls in all_estimators():
        try:
            estimator = cls()
        except Exception as exc:
            skipped.append((name, type(exc).__name__, str(exc)))
            continue

        try:
            tags = get_tags(estimator)
        except Exception as exc:
            skipped.append((name, type(exc).__name__, f"get_tags failed: {exc}"))
            continue

        # Broadly treat estimators exposing transform as transformer-like.
        # This deliberately keeps the denominator broad; the report limitation
        # should note that set_output is not equally relevant to every transformer.
        is_transformer = safe_callable(estimator, "fit") and safe_callable(
            estimator, "transform"
        )

        has_set_output = is_transformer and safe_callable(estimator, "set_output")
        array_api_support = bool(getattr(tags, "array_api_support", False))

        rows.append(
            {
                "estimator": name,
                "module": cls.__module__,
                "is_transformer": is_transformer,
                "set_output_supported": has_set_output,
                "array_api_support": array_api_support,
            }
        )

    output_csv = RESULTS_DIR / "data_exchange_coverage.csv"
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    total_estimators = len(rows)
    transformers = [r for r in rows if r["is_transformer"]]
    set_output_supported = [r for r in transformers if r["set_output_supported"]]
    array_api_supported = [r for r in rows if r["array_api_support"]]

    set_output_rate = (
        100.0 * len(set_output_supported) / len(transformers) if transformers else 0.0
    )
    array_api_rate = (
        100.0 * len(array_api_supported) / total_estimators
        if total_estimators
        else 0.0
    )

    # Composite score: each applicable (component, capability) pair is one case.
    # set_output is counted for transformer-like estimators; Array API is counted
    # for all estimators. Report the two sub-rates as well so the composite is
    # not interpreted without context.
    applicable_pairs = len(transformers) + total_estimators
    supported_pairs = len(set_output_supported) + len(array_api_supported)
    combined_rate = (
        100.0 * supported_pairs / applicable_pairs if applicable_pairs else 0.0
    )

    summary = f"""Data exchange coverage
======================

scikit-learn version: {sklearn.__version__}
Imported from: {Path(sklearn.__file__).resolve()}
Git commit: {git_commit()}

Instantiated estimators: {total_estimators}
Skipped estimators: {len(skipped)}

set_output coverage:
  Supported transformer-like estimators: {len(set_output_supported)}
  Transformer-like estimators: {len(transformers)}
  Coverage: {set_output_rate:.2f}%

Array API coverage:
  Estimators with array_api_support=True: {len(array_api_supported)}
  All instantiated estimators: {total_estimators}
  Coverage: {array_api_rate:.2f}%

Combined applicable capability-pair coverage:
  Supported pairs: {supported_pairs}
  Applicable pairs: {applicable_pairs}
  Coverage: {combined_rate:.2f}%

Important:
- Report the two sub-rates separately even if you also use the combined value.
- set_output is not equally applicable to every transformer-like estimator.
- Array API support is taken from scikit-learn's estimator tags.
"""

    if skipped:
        summary += "\nSkipped estimators:\n"
        for name, exc_type, msg in skipped:
            summary += f"  - {name}: {exc_type}: {msg}\n"

    summary_file = RESULTS_DIR / "data_exchange_coverage_summary.txt"

    summary_file.write_text(
    summary, encoding="utf-8"
)
    print(summary)
    print(f"Wrote: {output_csv}")
    print(f"Wrote: {summary_file}")


if __name__ == "__main__":
    main()
