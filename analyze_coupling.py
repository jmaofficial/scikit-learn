from pathlib import Path
from collections import defaultdict
import ast
import csv
import importlib.util

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
SKLEARN_DIR = REPO_ROOT / "sklearn"
OUTPUT_FILE = REPO_ROOT / "coupling_results.csv"

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
    "analyze_dependencies.py",
    "analyze_inheritance.py",
}

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def get_component(file_path):
    """
    Examples:
        sklearn/ensemble/_forest.py -> ensemble
        sklearn/svm/_classes.py     -> svm
        sklearn/base.py             -> base
        sklearn/pipeline.py         -> pipeline
    """
    relative = file_path.relative_to(SKLEARN_DIR)

    if len(relative.parts) == 1:
        return file_path.stem

    return relative.parts[0]


def get_python_files():
    files = []

    for file_path in SKLEARN_DIR.rglob("*.py"):

        if any(
            part in EXCLUDED_DIRS
            for part in file_path.relative_to(SKLEARN_DIR).parts
        ):
            continue

        if file_path.name in EXCLUDED_FILES:
            continue

        files.append(file_path)

    return sorted(files)


def get_current_package(file_path):
    """
    Return the fully qualified package containing a file.

    sklearn/ensemble/_forest.py -> sklearn.ensemble
    sklearn/ensemble/__init__.py -> sklearn.ensemble
    sklearn/base.py -> sklearn
    """
    relative = file_path.relative_to(SKLEARN_DIR)

    if file_path.name == "__init__.py":
        parts = relative.parts[:-1]
    else:
        parts = relative.parts[:-1]

    return ".".join(("sklearn", *parts))


def resolve_import(node, current_package):
    """
    Resolve absolute and relative imports.

    Returns possible imported module paths.
    """
    imports = []

    if isinstance(node, ast.Import):
        for alias in node.names:
            imports.append(alias.name)

    elif isinstance(node, ast.ImportFrom):

        if node.level == 0:
            base_module = node.module or ""

        else:
            relative_name = "." * node.level + (node.module or "")

            try:
                base_module = importlib.util.resolve_name(
                    relative_name,
                    current_package
                )
            except ImportError:
                return []

        if base_module:
            imports.append(base_module)

        # Handle imports such as:
        # from sklearn import base
        # from . import _forest
        for alias in node.names:
            if alias.name == "*":
                continue

            imports.append(f"{base_module}.{alias.name}")

    return imports


def imported_component(module_name, valid_components):
    """
    Map sklearn module paths to top-level components.

    sklearn.ensemble._forest -> ensemble
    sklearn.base             -> base
    sklearn.utils.validation -> utils
    """
    parts = module_name.split(".")

    if len(parts) < 2 or parts[0] != "sklearn":
        return None

    component = parts[1]

    if component in valid_components:
        return component

    return None


# --------------------------------------------------
# ANALYSIS
# --------------------------------------------------

def analyze_repository():

    if not SKLEARN_DIR.is_dir():
        raise FileNotFoundError(
            f"Could not find sklearn directory: {SKLEARN_DIR}"
        )

    python_files = get_python_files()

    # Include all components, even if they have no dependencies
    components = {
        get_component(file_path)
        for file_path in python_files
    }

    dependencies = defaultdict(set)
    import_counts = defaultdict(int)

    skipped_files = 0

    for file_path in python_files:

        source_component = get_component(file_path)

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))

        except (SyntaxError, UnicodeDecodeError) as error:
            print(f"Skipping {file_path}: {error}")
            skipped_files += 1
            continue

        current_package = get_current_package(file_path)

        for node in ast.walk(tree):

            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue

            imported_modules = resolve_import(
                node,
                current_package
            )

            # Avoid counting the same component multiple
            # times within one import statement
            targets = set()

            for module_name in imported_modules:

                target_component = imported_component(
                    module_name,
                    components
                )

                if target_component is None:
                    continue

                # Ignore internal imports within the same component
                if target_component == source_component:
                    continue

                targets.add(target_component)

            for target in targets:

                dependencies[source_component].add(target)

                import_counts[
                    (source_component, target)
                ] += 1

    # --------------------------------------------------
    # CALCULATE FAN-IN / FAN-OUT
    # --------------------------------------------------

    fan_out = {
        component: len(dependencies[component])
        for component in components
    }

    fan_in = defaultdict(int)

    for source, targets in dependencies.items():
        for target in targets:
            fan_in[target] += 1

    # Sort by fan-out (largest first)
    sorted_components = sorted(
        components,
        key=lambda component: fan_out[component],
        reverse=True
    )

    # --------------------------------------------------
    # SAVE CSV
    # --------------------------------------------------

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as csvfile:

        writer = csv.writer(csvfile)

        writer.writerow([
            "module",
            "fan_out",
            "fan_in",
        ])

        for component in sorted_components:

            writer.writerow([
                component,
                fan_out[component],
                fan_in[component],
            ])

    # --------------------------------------------------
    # PRINT RESULTS
    # --------------------------------------------------

    print("\n=== PACKAGE COUPLING ANALYSIS ===\n")

    print(
        f"{'Module':<25} "
        f"{'Fan-out':>10} "
        f"{'Fan-in':>10}"
    )

    print("-" * 49)

    for component in sorted_components:

        print(
            f"{component:<25} "
            f"{fan_out[component]:>10} "
            f"{fan_in[component]:>10}"
        )

    total_dependencies = sum(
        len(targets)
        for targets in dependencies.values()
    )

    print("\n=== SUMMARY ===")
    print(f"Components analyzed: {len(components)}")
    print(f"Python files analyzed: {len(python_files)}")
    print(f"Unique dependencies: {total_dependencies}")
    print(f"Skipped files: {skipped_files}")
    print(f"\nResults saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    analyze_repository()