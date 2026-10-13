import ast
from pathlib import Path
from collections import defaultdict, Counter

SKLEARN_DIR = Path(__file__).resolve().parent

# Classes we are especially interested in architecturally
IMPORTANT_BASES = {
    "BaseEstimator",
    "ClassifierMixin",
    "RegressorMixin",
    "TransformerMixin",
    "ClusterMixin",
    "OutlierMixin",
    "MetaEstimatorMixin",
}

def generate_overview_graph(package_counts):
    dot = [
        "digraph Architecture {",
        '  rankdir=TB;',
        '  node [shape=box, style="rounded"];',
        '',
        '  BaseEstimator [shape=ellipse];',
        ''
    ]

    mixins = [
        "ClassifierMixin",
        "RegressorMixin",
        "TransformerMixin",
        "ClusterMixin",
        "OutlierMixin",
        "MetaEstimatorMixin",
    ]

    for mixin in mixins:
        dot.append(f'  "{mixin}" -> "BaseEstimator" [label="extends"];')

    for package, count in package_counts.items():
        dot.append(
            f'  "{package}\\n{count} classes" -> '
            f'"BaseEstimator" [label="ultimately extends"];'
        )

    dot.append("}")

    Path("inheritance_overview.dot").write_text(
        "\n".join(dot),
        encoding="utf-8"
    )

def get_package(file_path: Path) -> str:
    """
    sklearn/ensemble/_forest.py -> ensemble
    sklearn/linear_model/_logistic.py -> linear_model
    sklearn/pipeline.py -> pipeline
    """
    relative = file_path.relative_to(SKLEARN_DIR)

    if len(relative.parts) == 1:
        return relative.stem

    return relative.parts[0]


def get_name(node):
    """
    Convert an AST expression representing a class/base into a readable name.

    Examples:
        BaseEstimator
        sklearn.base.BaseEstimator
        SomeGeneric[T]
    """
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = get_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    if isinstance(node, ast.Subscript):
        return get_name(node.value)

    return None


def short_name(name):
    """
    sklearn.base.BaseEstimator -> BaseEstimator
    """
    if not name:
        return None

    return name.split(".")[-1]


def is_test_file(file_path: Path) -> bool:
    """
    Ignore test infrastructure so it does not distort
    the architectural analysis.
    """
    return (
        "tests" in file_path.parts
        or "_test_common" in file_path.parts
        or file_path.name == "estimator_checks.py"
        or file_path.name == "conftest.py"
    )


# class name -> information about class
classes = {}

# base class -> list of children
children = defaultdict(list)


def analyze_file(file_path: Path):
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as error:
        print(f"Could not parse {file_path}: {error}")
        return

    package = get_package(file_path)

    for node in ast.walk(tree):

        if not isinstance(node, ast.ClassDef):
            continue

        bases = []

        for base in node.bases:
            name = get_name(base)

            if name:
                bases.append(name)

        class_info = {
            "name": node.name,
            "package": package,
            "file": str(file_path),
            "line": node.lineno,
            "bases": bases,
        }

        # Use file + class name as unique identifier
        class_id = f"{file_path}:{node.name}"

        classes[class_id] = class_info

        for base in bases:
            children[short_name(base)].append(class_info)


def build_name_index():
    """
    Maps short class names to all definitions with that name.
    """
    index = defaultdict(list)

    for class_id, info in classes.items():
        index[info["name"]].append((class_id, info))

    return index


def ultimately_inherits_from(class_id, target, name_index, visited=None):
    """
    Follow inheritance recursively to determine whether a class
    ultimately inherits from a target such as BaseEstimator.
    """
    if visited is None:
        visited = set()

    if class_id in visited:
        return False

    visited.add(class_id)

    info = classes[class_id]

    for base in info["bases"]:
        base_short = short_name(base)

        if base_short == target:
            return True

        # Follow the base if its definition exists inside sklearn
        for parent_id, _ in name_index.get(base_short, []):
            if ultimately_inherits_from(
                parent_id,
                target,
                name_index,
                visited.copy(),
            ):
                return True

    return False


def main():
    python_files = [
        file
        for file in SKLEARN_DIR.rglob("*.py")
        if not is_test_file(file)
    ]

    print(f"Analyzing {len(python_files)} Python files...\n")

    for file_path in python_files:
        analyze_file(file_path)

    name_index = build_name_index()

    print("=" * 80)
    print("MOST COMMON BASE CLASSES")
    print("=" * 80)

    base_counts = Counter()

    for info in classes.values():
        for base in info["bases"]:
            base_counts[short_name(base)] += 1

    for base, count in base_counts.most_common(30):
        print(f"{base:<35} {count} direct subclasses")

    print("\n")
    print("=" * 80)
    print("IMPORTANT SCIKIT-LEARN EXTENSION BASES")
    print("=" * 80)

    for base in sorted(IMPORTANT_BASES):
        direct = children.get(base, [])

        print(f"\n{base}")
        print(f"    Direct subclasses/users: {len(direct)}")

        for info in sorted(
            direct,
            key=lambda x: (x["package"], x["name"])
        ):
            print(
                f"    <- {info['package']}.{info['name']}"
                f"    ({info['file']}:{info['line']})"
            )

    print("\n")
    print("=" * 80)
    print("CLASSES THAT ULTIMATELY INHERIT FROM BaseEstimator")
    print("=" * 80)

    estimator_classes = []

    for class_id, info in classes.items():

        if info["name"] == "BaseEstimator":
            continue

        if ultimately_inherits_from(
            class_id,
            "BaseEstimator",
            name_index,
        ):
            estimator_classes.append(info)

    estimator_classes.sort(
        key=lambda x: (x["package"], x["name"])
    )

    package_counts = Counter(
        info["package"]
        for info in estimator_classes
    )

    print(
        f"\nTotal classes ultimately inheriting from "
        f"BaseEstimator: {len(estimator_classes)}\n"
    )

    print("By package:")

    for package, count in package_counts.most_common():
        print(f"    {package:<25} {count}")

    print("\nConcrete inheritance examples:")

    for info in estimator_classes:
        bases = ", ".join(info["bases"])

        print(
            f"    {info['package']}.{info['name']}"
            f" -> [{bases}]"
        )

    print("\n")
    print("=" * 80)
    print("MIXIN USAGE")
    print("=" * 80)

    mixins = [
        "ClassifierMixin",
        "RegressorMixin",
        "TransformerMixin",
        "ClusterMixin",
        "OutlierMixin",
        "MetaEstimatorMixin",
    ]

    for mixin in mixins:

        users = []

        for class_id, info in classes.items():

            if ultimately_inherits_from(
                class_id,
                mixin,
                name_index,
            ):
                users.append(info)

        packages = Counter(
            info["package"]
            for info in users
        )

        print(f"\n{mixin}: {len(users)} classes")

        for package, count in packages.most_common():
            print(f"    {package:<25} {count}")

    print("\n")
    print("=" * 80)
    print("ARCHITECTURAL SUMMARY")
    print("=" * 80)

    print(
        f"Total classes analyzed: {len(classes)}"
    )

    print(
        f"Classes ultimately extending BaseEstimator: "
        f"{len(estimator_classes)}"
    )

    print(
        f"Packages containing BaseEstimator descendants: "
        f"{len(package_counts)}"
    )

    print("\nPackages extending the estimator framework:")

    for package, count in package_counts.most_common():
        print(f"    {package:<25} {count}")

    generate_overview_graph(package_counts)
if __name__ == "__main__":
    main()