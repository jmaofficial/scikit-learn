from pathlib import Path
import csv
import io
import tokenize
from collections import defaultdict

# Paths
REPO_ROOT = Path(__file__).resolve().parent
SKLEARN_DIR = REPO_ROOT / "sklearn"
OUTPUT_FILE = REPO_ROOT / "loc_results.csv"

# Directories and files to exclude
EXCLUDED_DIRS = {
    "tests",
    "__pycache__",
    "_test_common",
}

EXCLUDED_FILES = {
    "conftest.py",
    "estimator_checks.py",
}


def count_code_lines(file_path):
    """
    Count non-empty, non-comment Python source lines.

    Uses tokenize to distinguish actual comments from
    '#' characters inside strings.
    """
    source = file_path.read_bytes()

    code_lines = set()
    excluded_tokens = {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
        tokenize.ENCODING,
    }

    try:
        for token in tokenize.tokenize(io.BytesIO(source).readline):
            if token.type in excluded_tokens:
                continue

            for line_number in range(token.start[0], token.end[0] + 1):
                code_lines.add(line_number)

    except (tokenize.TokenError, SyntaxError, IndentationError):
        print(f"Warning: Could not tokenize {file_path}")
        return None

    return len(code_lines)


def get_module_name(file_path):
    """
    Determine the top-level component.

    Examples:
        sklearn/ensemble/_forest.py -> ensemble
        sklearn/svm/_classes.py     -> svm
        sklearn/base.py             -> base
        sklearn/pipeline.py         -> pipeline
    """
    relative_path = file_path.relative_to(SKLEARN_DIR)

    if len(relative_path.parts) == 1:
        return file_path.stem

    return relative_path.parts[0]


def analyze_repository():
    if not SKLEARN_DIR.is_dir():
        raise FileNotFoundError(
            f"Could not find sklearn directory: {SKLEARN_DIR}"
        )

    results = defaultdict(lambda: {
        "files": 0,
        "loc": 0,
    })

    total_files = 0
    skipped_files = 0

    for file_path in SKLEARN_DIR.rglob("*.py"):

        # Exclude tests and other non-production code
        if any(part in EXCLUDED_DIRS for part in file_path.parts):
            continue

        if file_path.name in EXCLUDED_FILES:
            continue

        module = get_module_name(file_path)
        loc = count_code_lines(file_path)

        if loc is None:
            skipped_files += 1
            continue

        results[module]["files"] += 1
        results[module]["loc"] += loc

        total_files += 1

    # Sort by LOC (largest first)
    sorted_results = sorted(
        results.items(),
        key=lambda item: item[1]["loc"],
        reverse=True
    )

    # Save CSV
    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow([
            "module",
            "python_files",
            "loc",
        ])

        for module, data in sorted_results:
            writer.writerow([
                module,
                data["files"],
                data["loc"],
            ])

    # Print summary
    print("\n=== PYTHON LINES OF CODE ANALYSIS ===\n")

    print(f"{'Module':<25} {'Files':>8} {'LOC':>10}")
    print("-" * 45)

    for module, data in sorted_results:
        print(
            f"{module:<25} "
            f"{data['files']:>8} "
            f"{data['loc']:>10}"
        )

    total_loc = sum(data["loc"] for data in results.values())

    print("\n=== SUMMARY ===")
    print(f"Components analyzed: {len(results)}")
    print(f"Python files analyzed: {total_files}")
    print(f"Total Python LOC: {total_loc:,}")
    print(f"Average LOC per component: {total_loc / len(results):,.1f}")
    print(f"Skipped files: {skipped_files}")
    print(f"\nResults saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    analyze_repository()