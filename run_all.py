from pathlib import Path
import subprocess
import sys
import shutil
import os

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

ANALYSIS_SCRIPTS = [
    "analyze_loc.py",
    "analyze_coupling.py",
    "analyze_complexity.py",
    "couplingchange.py",
]

VISUALIZATION_SCRIPTS = [
    "visualize_loc.py",
    "visualize_coupling.py",
    "visualize_complexity.py",
]

CSV_FILES = [
    "loc_results.csv",
    "coupling_results.csv",
    "complexity_results.csv",
]

# All supported visualization formats
IMAGE_EXTENSIONS = {".png", ".svg", ".pdf"}

# Known output filenames from previous versions
KNOWN_IMAGES = {
    "loc_by_module.png",
    "loc_by_module.svg",
    "loc_visualization.png",
    "coupling_by_module.svg",
    "coupling_visualization.png",
    "coupling_visualization.pdf",
    "coupling_visualization.svg",
    "complexity_visualization.png",
    "complexity_visualization.pdf",
    "complexity_visualization.svg",
    "cyclomatic_complexity_by_module.png",
    "cyclomatic_complexity_by_module.svg",
}


def clean_results():
    print("\n=== CLEANING OLD RESULTS ===", flush=True)

    # Delete old results folder
    if RESULTS.exists():
        shutil.rmtree(RESULTS)

    RESULTS.mkdir(parents=True)

    # Delete old CSV files from root
    for filename in CSV_FILES:
        path = ROOT / filename

        if path.exists():
            path.unlink()
            print(f"Removed: {filename}")

    # Delete only known generated images from root
    for filename in KNOWN_IMAGES:
        path = ROOT / filename

        if path.exists():
            path.unlink()
            print(f"Removed: {filename}")

    print("Created clean results/ directory")


def run_script(script, env):
    script_path = ROOT / script

    if not script_path.is_file():
        raise FileNotFoundError(
            f"Required script not found: {script_path}"
        )

    print(f"\nRunning {script}...", flush=True)

    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT,
        env=env,
        check=True
    )

    print(f"Completed: {script}", flush=True)


def collect_csv():
    print("\n=== COLLECTING CSV FILES ===", flush=True)

    for filename in CSV_FILES:
        source = ROOT / filename
        destination = RESULTS / filename

        # Some scripts already save directly in results/
        if source.exists():
            shutil.move(str(source), str(destination))
            print(f"Moved: {filename} -> results/")

        if not destination.is_file():
            raise FileNotFoundError(
                f"Missing analysis result: {filename}"
            )

        print(f"OK: {filename}")


def collect_images():
    print("\n=== COLLECTING VISUALIZATIONS ===", flush=True)

    # Move generated images from root into results/
    for filename in KNOWN_IMAGES:
        source = ROOT / filename
        destination = RESULTS / filename

        if source.is_file():
            shutil.move(str(source), str(destination))
            print(f"Moved: {filename} -> results/")

    # Show all generated images
    images = sorted(
        path
        for path in RESULTS.iterdir()
        if path.is_file()
        and path.suffix.lower() in IMAGE_EXTENSIONS
    )

    for image in images:
        print(f"OK: {image.name}")

    # Verify each analysis has at least one visualization
    expected = {
        "LOC": ("loc_",),
        "Coupling": ("coupling_",),
        "Complexity": ("complexity_", "cyclomatic_"),
    }

    missing = []

    for analysis, prefixes in expected.items():
        found = any(
            image.name.startswith(prefixes)
            for image in images
        )

        if not found:
            missing.append(analysis)

    if missing:
        raise RuntimeError(
            "Missing visualizations for: "
            + ", ".join(missing)
        )


def print_summary():
    print("\n======================================")
    print(" ANALYSIS COMPLETED SUCCESSFULLY")
    print("======================================")

    files = sorted(RESULTS.iterdir())

    print("\nGenerated files:")

    for file in files:
        if file.is_file():
            print(f"  results/{file.name}")

    print(f"\nTotal files: {len(files)}")
    print(f"Results directory: {RESULTS}")


def main():
    print("======================================")
    print(" SCIKIT-LEARN ARCHITECTURE ANALYSIS")
    print("======================================")

    # Set output directory for all scripts
    env = os.environ.copy()
    env["RESULTS_DIR"] = str(RESULTS)

    # Avoid blocking on plt.show() during batch execution
    env["MPLBACKEND"] = "Agg"

    # Step 1: Clean old results
    clean_results()

    # Step 2: Run analyses
    print("\n=== RUNNING ANALYSES ===", flush=True)

    for script in ANALYSIS_SCRIPTS:
        run_script(script, env)

    # Step 3: Ensure all CSV files are in results/
    collect_csv()

    # Step 4: Generate visualizations
    print("\n=== GENERATING VISUALIZATIONS ===", flush=True)

    for script in VISUALIZATION_SCRIPTS:
        run_script(script, env)

    # Step 5: Collect and verify images
    collect_images()

    # Step 6: Print summary
    print_summary()


if __name__ == "__main__":
    try:
        main()

    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        sys.exit(1)