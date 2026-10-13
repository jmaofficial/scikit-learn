from pathlib import Path
import csv
import os
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent

RESULTS_DIR = Path(
    os.environ.get("RESULTS_DIR", REPO_ROOT / "results")
)

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = RESULTS_DIR / "complexity_results.csv"
OUTPUT_FILE = RESULTS_DIR / "complexity_visualization.png"


def load_results():
    results = []

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            results.append({
                "module": row["module"],
                "average_complexity": float(row["average_complexity"]),
                "max_complexity": int(row["max_complexity"]),
                "functions": int(row["functions"])
            })

    return sorted(results, key=lambda x: x["average_complexity"])


def visualize(results):
    modules = [row["module"] for row in results]
    averages = [row["average_complexity"] for row in results]

    fig, ax = plt.subplots(figsize=(12, 15))

    ax.barh(modules, averages)

    ax.set_xlabel("Average Cyclomatic Complexity (Radon)")
    ax.set_ylabel("Top-level Component")
    ax.set_title(
        "Scikit-learn - Average Cyclomatic Complexity by Component"
    )

    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight")
    plt.show()

    print(f"Visualization saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Could not find {INPUT_FILE}. Run analyze_complexity.py first."
        )

    results = load_results()
    visualize(results)