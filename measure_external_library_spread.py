#!/usr/bin/env python3
"""
Metric 2: External library spread

Static AST analysis of productive Python files under sklearn/.

Default target libraries:
- pandas
- polars

Run from the scikit-learn repository root:
    python measure_external_library_spread.py

Optionally choose other libraries:
    python measure_external_library_spread.py --libraries pandas polars narwhals

It writes:
- external_library_spread.csv
- external_library_spread_summary.txt
"""

from __future__ import annotations

import argparse
import ast
import csv
from collections import Counter
from pathlib import Path

import os

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", ROOT / "results"))
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def productive_python_files(root: Path):
    for path in root.rglob("*.py"):
        # Exclude tests anywhere in the path.
        if "tests" in path.parts:
            continue
        if "__pycache__" in path.parts:
            continue
        yield path


def imported_top_level_libraries(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()

    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])

    return imports


def top_level_component(path: Path, sklearn_root: Path) -> str:
    rel = path.relative_to(sklearn_root)
    first = rel.parts[0]
    if len(rel.parts) == 1:
        return "(sklearn root)"
    return first


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to scikit-learn repository root (default: current directory).",
    )
    parser.add_argument(
        "--libraries",
        nargs="+",
        default=["pandas", "polars"],
        help="External libraries to count (default: pandas polars).",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    sklearn_root = repo_root / "sklearn"
    if not sklearn_root.is_dir():
        raise SystemExit(
            f"Could not find {sklearn_root}. Run from the repository root "
            "or pass --repo PATH."
        )

    target_libraries = set(args.libraries)
    files = list(productive_python_files(sklearn_root))

    rows = []
    touched_files = []
    library_counts = Counter()
    component_counts = Counter()

    for path in files:
        imports = imported_top_level_libraries(path)
        matched = sorted(imports & target_libraries)

        if matched:
            rel = path.relative_to(repo_root).as_posix()
            component = top_level_component(path, sklearn_root)
            touched_files.append(rel)
            component_counts[component] += 1
            for lib in matched:
                library_counts[lib] += 1

            rows.append(
                {
                    "file": rel,
                    "top_level_component": component,
                    "matched_libraries": ",".join(matched),
                }
            )

    output_csv = RESULTS_DIR / "external_library_spread.csv"
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["file", "top_level_component", "matched_libraries"],
        )
        writer.writeheader()
        writer.writerows(rows)

    total_files = len(files)
    unique_touched = len(set(touched_files))
    spread_rate = 100.0 * unique_touched / total_files if total_files else 0.0

    summary_lines = [
        "External library spread",
        "=======================",
        "",
        f"Repository: {repo_root}",
        f"Target libraries: {', '.join(sorted(target_libraries))}",
        f"Productive Python files examined: {total_files}",
        f"Files with at least one direct target-library import: {unique_touched}",
        f"File spread: {spread_rate:.2f}%",
        "",
        "Files importing each library:",
    ]

    for lib in sorted(target_libraries):
        count = library_counts[lib]
        rate = 100.0 * count / total_files if total_files else 0.0
        summary_lines.append(f"  {lib}: {count} files ({rate:.2f}%)")

    summary_lines += ["", "Touched files by top-level component:"]
    for component, count in component_counts.most_common():
        summary_lines.append(f"  {component}: {count}")

    summary_lines += [
        "",
        "Important:",
        "- This counts direct import statements only.",
        "- Integration hidden behind helper modules or abstraction libraries will not be counted.",
        "- A low spread can therefore mean either good localization or indirect integration.",
    ]

    summary = "\n".join(summary_lines) + "\n"
    summary_file = RESULTS_DIR / "external_library_spread_summary.txt"

    summary_file.write_text(
    summary, encoding="utf-8"
)

    print(summary)
    print(f"Wrote: {output_csv}")
    print(f"Wrote: {summary_file}")


if __name__ == "__main__":
    main()
