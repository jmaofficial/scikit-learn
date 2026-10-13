from pathlib import Path
from collections import defaultdict
import csv

from radon.complexity import cc_visit

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

import os

RESULTS_DIR = Path(
    os.environ.get("RESULTS_DIR", Path(__file__).resolve().parent)
)

REPO_ROOT = Path(__file__).resolve().parent
SKLEARN_DIR = REPO_ROOT / "sklearn"
OUTPUT_FILE = RESULTS_DIR / "complexity_results.csv"

EXCLUDED_DIRS = {
    "tests",
    "__pycache__",
    "_test_common",
}

EXCLUDED_FILES = {
    "conftest.py",
    "estimator_checks.py",
    "analyze_loc.py",
    "analyze_coupling.py",
    "analyze_complexity.py",
    "analyze_dependencies.py",
    "analyze_inheritance.py",
}

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def get_component(file_path):
    relative = file_path.relative_to(SKLEARN_DIR)

    if len(relative.parts) == 1:
        return file_path.stem

    return relative.parts[0]


def get_python_files():
    files = []

    for file_path in SKLEARN_DIR.rglob("*.py"):

        relative = file_path.relative_to(SKLEARN_DIR)

        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue

        if file_path.name in EXCLUDED_FILES:
            continue

        files.append(file_path)

    return sorted(files)


# --------------------------------------------------
# ANALYSIS
# --------------------------------------------------

def analyze_repository():

    if not SKLEARN_DIR.is_dir():
        raise FileNotFoundError(
            f"Could not find sklearn directory: {SKLEARN_DIR}"
        )

    results = defaultdict(list)
    skipped_files = 0
    analyzed_files = 0

    for file_path in get_python_files():

        component = get_component(file_path)

        try:
            source = file_path.read_text(encoding="utf-8")
            blocks = cc_visit(source)

        except (SyntaxError, UnicodeDecodeError) as error:
            print(f"Skipping {file_path}: {error}")
            skipped_files += 1
            continue

        analyzed_files += 1

        for block in blocks:

            # Functions defined outside classes
            if block.letter == "F":
                results[component].append(block.complexity)

            # Methods defined inside classes
            elif block.letter == "C":
                for method in block.methods:
                    results[component].append(method.complexity)

    # --------------------------------------------------
    # CALCULATE METRICS
    # --------------------------------------------------

    summary = []

    for component, complexities in results.items():

        count = len(complexities)

        average = sum(complexities) / count
        maximum = max(complexities)

        summary.append({
            "module": component,
            "functions": count,
            "average_complexity": average,
            "max_complexity": maximum,
        })

    summary.sort(
        key=lambda row: row["average_complexity"],
        reverse=True,
    )

    # --------------------------------------------------
    # SAVE CSV
    # --------------------------------------------------

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csvfile:

        writer = csv.writer(csvfile)

        writer.writerow([
            "module",
            "functions",
            "average_complexity",
            "max_complexity",
        ])

        for row in summary:

            writer.writerow([
                row["module"],
                row["functions"],
                round(row["average_complexity"], 2),
                row["max_complexity"],
            ])

    # --------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------

    print("\n=== CYCLOMATIC COMPLEXITY ANALYSIS ===\n")

    print(
        f"{'Module':<25}"
        f"{'Functions':>12}"
        f"{'Average CC':>15}"
        f"{'Max CC':>12}"
    )

    print("-" * 64)

    for row in summary:

        print(
            f"{row['module']:<25}"
            f"{row['functions']:>12}"
            f"{row['average_complexity']:>15.2f}"
            f"{row['max_complexity']:>12}"
        )

    print("\n=== SUMMARY ===")
    print(f"Python files analyzed: {analyzed_files}")
    print(f"Components analyzed: {len(summary)}")
    print(f"Skipped files: {skipped_files}")

    print(f"\nResults saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    analyze_repository()