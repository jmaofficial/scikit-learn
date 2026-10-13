import csv
import os
from pathlib import Path
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent

RESULTS_DIR = Path(
    os.environ.get("RESULTS_DIR", REPO_ROOT / "results")
)

INPUT_FILE = RESULTS_DIR / "loc_results.csv"
OUTPUT_PNG = RESULTS_DIR / "loc_by_module.png"
OUTPUT_SVG = RESULTS_DIR / "loc_by_module.svg"


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    modules = []
    loc_values = []

    with INPUT_FILE.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            modules.append(row["module"])
            loc_values.append(int(row["loc"]))

    # Horizontal bar chart
    fig, ax = plt.subplots(
        figsize=(12, max(6, len(modules) * 0.3))
    )

    ax.barh(modules, loc_values, height=0.7)

    ax.set_xlabel("Python Lines of Code")
    ax.set_ylabel("Module")
    ax.set_title("Scikit-learn: Python LOC by Top-Level Component")

    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)

    plt.tight_layout()

    fig.savefig(OUTPUT_PNG, dpi=300, bbox_inches="tight")
    fig.savefig(OUTPUT_SVG, bbox_inches="tight")

    plt.show()

    print(f"Saved: {OUTPUT_PNG}")
    print(f"Saved: {OUTPUT_SVG}")


if __name__ == "__main__":
    main()