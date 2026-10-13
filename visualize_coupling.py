from pathlib import Path
import csv
import matplotlib.pyplot as plt
import numpy as np
import os

REPO_ROOT = Path(__file__).resolve().parent

RESULTS_DIR = Path(
    os.environ.get("RESULTS_DIR", REPO_ROOT / "results")
)

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = RESULTS_DIR / "coupling_results.csv"
OUTPUT_FILE = RESULTS_DIR / "coupling_visualization.png"
PDF_FILE = RESULTS_DIR / "coupling_visualization.pdf"


def load_results():
    results = []

    with INPUT_FILE.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            results.append({
                "module": row["module"],
                "fan_in": int(row["fan_in"]),
                "fan_out": int(row["fan_out"])
            })

    return sorted(
        results,
        key=lambda x: x["fan_in"] + x["fan_out"],
        reverse=True
    )


def visualize(results):
    modules = [row["module"] for row in results]
    fan_in = np.array([row["fan_in"] for row in results])
    fan_out = np.array([row["fan_out"] for row in results])

    y = np.arange(len(modules))

    # Each pair of bars is centered around its module name
    bar_height = 0.35

    fig, ax = plt.subplots(
        figsize=(13, max(10, len(modules) * 0.45))
    )

    ax.barh(
        y - bar_height / 2,
        fan_in,
        height=bar_height,
        label="Fan-in",
        color="#4472C4"
    )

    ax.barh(
        y + bar_height / 2,
        fan_out,
        height=bar_height,
        label="Fan-out",
        color="#ED7D31"
    )

    ax.set_yticks(y)
    ax.set_yticklabels(modules, fontsize=9)

    # Highest coupling at top
    ax.invert_yaxis()

    ax.set_xlabel("Number of Dependencies")
    ax.set_ylabel("Component")
    ax.set_title(
        "Scikit-learn - Package Coupling by Component",
        fontsize=14
    )

    ax.legend(loc="lower right")

    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)

    # Add values at the end of each bar
    for i, value in enumerate(fan_in):
        if value > 0:
            ax.text(
                value + 0.3,
                y[i] - bar_height / 2,
                str(value),
                va="center",
                fontsize=8
            )

    for i, value in enumerate(fan_out):
        if value > 0:
            ax.text(
                value + 0.3,
                y[i] + bar_height / 2,
                str(value),
                va="center",
                fontsize=8
            )

    ax.set_xlim(0, max(max(fan_in), max(fan_out)) * 1.15)

    plt.tight_layout()

    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches="tight")
    plt.savefig(PDF_FILE, bbox_inches="tight")

    plt.show()

    print(f"PNG saved to: {OUTPUT_FILE}")
    print(f"PDF saved to: {PDF_FILE}")


if __name__ == "__main__":
    results = load_results()
    visualize(results)