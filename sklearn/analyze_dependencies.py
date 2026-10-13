import ast
from pathlib import Path
from collections import defaultdict, Counter

SKLEARN_DIR = Path(__file__).resolve().parent

# package -> Counter(dependency -> number of imports)
dependencies = defaultdict(Counter)

# Store concrete examples so we can inspect them later
examples = defaultdict(lambda: defaultdict(list))


def get_package(file_path: Path) -> str:
    """
    Convert:
        sklearn/ensemble/_forest.py -> ensemble
        sklearn/linear_model/_logistic.py -> linear_model
        sklearn/pipeline.py -> pipeline
    """
    relative = file_path.relative_to(SKLEARN_DIR)

    if len(relative.parts) == 1:
        return relative.stem

    return relative.parts[0]


def dependency_from_module(module: str):
    """
    Convert:
        sklearn.utils.validation -> utils
        sklearn.base             -> base
        sklearn.ensemble         -> ensemble
    """
    if not module.startswith("sklearn."):
        return None

    parts = module.split(".")

    if len(parts) >= 2:
        return parts[1]

    return None


def analyze_file(file_path: Path):
    source_package = get_package(file_path)

    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as error:
        print(f"Could not parse {file_path}: {error}")
        return

    for node in ast.walk(tree):

        # Example:
        # from sklearn.base import BaseEstimator
        if isinstance(node, ast.ImportFrom):

            if node.module:
                target = dependency_from_module(node.module)

                if target and target != source_package:
                    dependencies[source_package][target] += 1
                    examples[source_package][target].append(
                        (str(file_path), node.lineno)
                    )

        # Example:
        # import sklearn.utils
        elif isinstance(node, ast.Import):

            for alias in node.names:
                target = dependency_from_module(alias.name)

                if target and target != source_package:
                    dependencies[source_package][target] += 1
                    examples[source_package][target].append(
                        (str(file_path), node.lineno)
                    )


def main():

    python_files = list(SKLEARN_DIR.rglob("*.py"))

    # Ignore tests for the initial architecture analysis
    python_files = [
    file
    for file in python_files
    if "tests" not in file.parts
    and "_test_common" not in file.parts
    and file.name != "estimator_checks.py"
    and file.name != "conftest.py"
]

    print(f"Analyzing {len(python_files)} Python files...\n")

    for file_path in python_files:
        analyze_file(file_path)

    print("=" * 70)
    print("SCIKIT-LEARN PACKAGE DEPENDENCIES")
    print("=" * 70)

    for package in sorted(dependencies):

        print(f"\n{package}")

        for dependency, count in dependencies[package].most_common():
            print(f"    -> {dependency:<25} {count} imports")

    print("\n")
    print("=" * 70)
    print("MOST DEPENDED-UPON PACKAGES")
    print("=" * 70)

    incoming = Counter()

    for source, targets in dependencies.items():
        for target in targets:
            incoming[target] += 1

    for package, count in incoming.most_common():
        print(
            f"{package:<25} depended upon by "
            f"{count} other packages"
        )

    print("\n")
    print("=" * 70)
    print("EXAMPLE DEPENDENCIES")
    print("=" * 70)

    for source in sorted(examples):
        for target in sorted(examples[source]):

            file_path, line = examples[source][target][0]

            print(
                f"{source:<20} -> {target:<20} "
                f"example: {file_path}:{line}"
            )


if __name__ == "__main__":
    main()