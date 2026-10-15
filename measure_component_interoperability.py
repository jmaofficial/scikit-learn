#!/usr/bin/env python3
"""
Metric 3: Component interoperability

Measures API-level interoperability for components intended to participate
in standard scikit-learn composed workflows.

Relevant roles:
- Transformer role: expected to provide fit + transform
- Predictive estimator role (classifier/regressor): expected to provide fit + predict

The script uses scikit-learn estimator tags to identify intended roles and
checks whether the corresponding standard interface is implemented.

It writes:
- component_interoperability.csv
- component_interoperability_summary.txt

Run from the scikit-learn repository root in an environment importing the
version/commit that you want to measure.
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
            tags = get_tags(estimator)
        except Exception as exc:
            skipped.append((name, type(exc).__name__, str(exc)))
            continue

        estimator_type = getattr(tags, "estimator_type", None)
        transformer_tags = getattr(tags, "transformer_tags", None)

        transformer_role = (
            transformer_tags is not None or estimator_type == "transformer"
        )
        predictor_role = estimator_type in {"classifier", "regressor"}

        relevant = transformer_role or predictor_role
        if not relevant:
            continue

        has_fit = safe_callable(estimator, "fit")
        has_transform = safe_callable(estimator, "transform")
        has_fit_transform = safe_callable(estimator, "fit_transform")
        has_predict = safe_callable(estimator, "predict")

        transformer_compatible = (
            (has_fit and has_transform) if transformer_role else None
        )
        predictor_compatible = (
            (has_fit and has_predict) if predictor_role else None
        )

        applicable_checks = []
        if transformer_role:
            applicable_checks.append(bool(transformer_compatible))
        if predictor_role:
            applicable_checks.append(bool(predictor_compatible))

        fully_compatible = all(applicable_checks)

        rows.append(
            {
                "estimator": name,
                "module": cls.__module__,
                "estimator_type": estimator_type,
                "transformer_role": transformer_role,
                "predictor_role": predictor_role,
                "has_fit": has_fit,
                "has_transform": has_transform,
                "has_fit_transform": has_fit_transform,
                "has_predict": has_predict,
                "transformer_role_compatible": transformer_compatible,
                "predictor_role_compatible": predictor_compatible,
                "fully_compatible": fully_compatible,
            }
        )

    output_csv = RESULTS_DIR / "component_interoperability.csv"
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    total = len(rows)
    compatible = sum(r["fully_compatible"] for r in rows)
    overall_rate = 100.0 * compatible / total if total else 0.0

    transformer_rows = [r for r in rows if r["transformer_role"]]
    transformer_ok = sum(
        r["transformer_role_compatible"] is True for r in transformer_rows
    )
    transformer_rate = (
        100.0 * transformer_ok / len(transformer_rows)
        if transformer_rows
        else 0.0
    )

    predictor_rows = [r for r in rows if r["predictor_role"]]
    predictor_ok = sum(
        r["predictor_role_compatible"] is True for r in predictor_rows
    )
    predictor_rate = (
        100.0 * predictor_ok / len(predictor_rows)
        if predictor_rows
        else 0.0
    )

    summary = f"""Component interoperability
==========================

scikit-learn version: {sklearn.__version__}
Imported from: {Path(sklearn.__file__).resolve()}
Git commit: {git_commit()}

Relevant instantiated components: {total}
Fully interface-compatible components: {compatible}
Overall compatibility: {overall_rate:.2f}%

Transformer-role compatibility:
  Compatible: {transformer_ok}
  Relevant transformers: {len(transformer_rows)}
  Coverage: {transformer_rate:.2f}%

Predictive-estimator-role compatibility:
  Compatible: {predictor_ok}
  Relevant classifiers/regressors: {len(predictor_rows)}
  Coverage: {predictor_rate:.2f}%

Skipped during instantiation/tag inspection: {len(skipped)}

Interpretation:
- Transformer role checks fit + transform, matching the interface needed for
  intermediate Pipeline/ColumnTransformer-style composition.
- Predictive estimator role checks fit + predict, matching a standard final
  predictive step.
- fit_transform is reported in the CSV but is not required, because fit +
  transform is sufficient for the transformer role.

Limitation:
This is API-level interoperability. It does not prove that every pair of
components is semantically compatible with every other pair or with every
dataset shape/type.
"""

    if skipped:
        summary += "\nSkipped estimators:\n"
        for name, exc_type, msg in skipped:
            summary += f"  - {name}: {exc_type}: {msg}\n"

    summary_file = RESULTS_DIR / "component_interoperability_summary.txt"

    summary_file.write_text(
    summary, encoding="utf-8"
)
    print(summary)
    print(f"Wrote: {output_csv}")
    print(f"Wrote: {summary_file}")


if __name__ == "__main__":
    main()
