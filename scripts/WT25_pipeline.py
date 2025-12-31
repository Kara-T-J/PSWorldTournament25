import argparse
import os
import shutil
import subprocess
import sys


def run_step(label, args):
    print(f"==> {label}")
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description="Run WT25 data pipeline end-to-end.")
    parser.add_argument("--raw", default="data/source/WT25_notes_raw.xlsx", help="Raw notes file.")
    parser.add_argument("--sheet", default="Notes2", help="Sheet name in the raw file.")
    parser.add_argument("--cleaned", default="data/intermediate/WT25_notes_cleaned.xlsx", help="Cleaned output file.")
    parser.add_argument("--zscore", default="data/intermediate/WT25_zscore.xlsx", help="Z-score output file.")
    parser.add_argument("--no-cluster", action="store_true", help="Skip clustering step.")
    parser.add_argument("--no-dashboard", action="store_true", help="Skip launching the dashboard.")
    args = parser.parse_args()

    python = sys.executable

    for path in ("data/intermediate", "data/output"):
        if os.path.isdir(path):
            shutil.rmtree(path)
        os.makedirs(path, exist_ok=True)

    run_step(
        "Cleaning notes",
        [
            python,
            "scripts/WT25_data_cleaning.py",
            "--input",
            args.raw,
            "--output",
            args.cleaned,
            "--sheet",
            args.sheet,
        ],
    )

    run_step(
        "Building z-score matrix + rank",
        [
            python,
            "scripts/WT25_zscore_builder.py",
            "--input",
            args.cleaned,
            "--output",
            args.zscore,
        ],
    )

    if args.no_cluster:
        return

    run_step(
        "Clustering participants",
        [
            python,
            "scripts/WT25_participant_clustering.py",
            "--input",
            args.zscore,
        ],
    )

    if args.no_dashboard:
        return

    run_step(
        "Launching dashboard",
        [
            python,
            "uiux/dashboard/app_dashboard.py",
        ],
    )


if __name__ == "__main__":
    main()
