#!/usr/bin/env python3
"""Unified generator: runs all data generation scripts for a GenomeDataLakeTables database.

Usage:
    python scripts/generate_all.py --db /path/to/database.db [--output-dir data/]
"""

import argparse
import os
import subprocess
import sys
import time

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Scripts to run in order (generate_phenotypes_data appends to genes_data.json,
# so it must run after generate_genes_data)
SCRIPTS = [
    ("generate_metadata.py", ["db", "output"]),
    ("generate_genes_data.py", ["db", "output"]),
    ("generate_phenotypes_data.py", ["db", "genes_data"]),
    ("generate_tree_data.py", ["db", "output"]),
    ("generate_reactions_data.py", ["db", "genes_data", "output"]),
    ("generate_cluster_data.py", ["db", "genes_data", "output"]),
    ("generate_summary_stats.py", ["db", "output"]),
]

OUTPUT_FILES = {
    "generate_metadata.py": "metadata.json",
    "generate_genes_data.py": "genes_data.json",
    "generate_phenotypes_data.py": None,  # modifies genes_data.json in place
    "generate_tree_data.py": "tree_data.json",
    "generate_reactions_data.py": "reactions_data.json",
    "generate_cluster_data.py": "cluster_data.json",
    "generate_summary_stats.py": "summary_stats.json",
}


def main():
    parser = argparse.ArgumentParser(
        description="Generate all data files for the Datalake Dashboard"
    )
    parser.add_argument(
        "--db", required=True,
        help="Path to GenomeDataLakeTables SQLite database"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Output directory for data files (default: ../data/ relative to scripts/)"
    )
    parser.add_argument(
        "--skip", nargs="*", default=[],
        help="Scripts to skip (e.g. --skip phenotypes summary)"
    )
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found: {db_path}")
        sys.exit(1)

    if args.output_dir:
        output_dir = os.path.abspath(args.output_dir)
    else:
        output_dir = os.path.abspath(os.path.join(SCRIPTS_DIR, "..", "data"))

    os.makedirs(output_dir, exist_ok=True)

    print(f"Database: {db_path}")
    print(f"Output:   {output_dir}")
    print(f"{'=' * 60}")

    skip_keywords = [s.lower() for s in args.skip]
    total_time = 0
    failed = []

    for script_name, arg_types in SCRIPTS:
        if any(kw in script_name.lower() for kw in skip_keywords):
            print(f"\nSKIPPING {script_name}")
            continue

        script_path = os.path.join(SCRIPTS_DIR, script_name)
        if not os.path.exists(script_path):
            print(f"\nWARNING: {script_name} not found, skipping")
            continue

        cmd_args = [sys.executable, script_path]
        for arg_type in arg_types:
            if arg_type == "db":
                cmd_args.append(db_path)
            elif arg_type == "output":
                out_file = OUTPUT_FILES.get(script_name)
                if out_file:
                    cmd_args.append(os.path.join(output_dir, out_file))
            elif arg_type == "genes_data":
                cmd_args.append(os.path.join(output_dir, "genes_data.json"))

        print(f"\n{'─' * 60}")
        print(f"Running {script_name}...")
        print(f"  Command: {' '.join(cmd_args)}")
        print(f"{'─' * 60}")

        start = time.time()
        result = subprocess.run(cmd_args, capture_output=False)
        elapsed = time.time() - start
        total_time += elapsed

        if result.returncode != 0:
            print(f"  FAILED (exit code {result.returncode})")
            failed.append(script_name)
        else:
            print(f"  Completed in {elapsed:.1f}s")

    print(f"\n{'=' * 60}")
    print(f"Total time: {total_time:.1f}s")

    if failed:
        print(f"FAILED scripts: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("All scripts completed successfully!")
        print(f"\nOutput files in {output_dir}:")
        for script_name, out_file_name in OUTPUT_FILES.items():
            if out_file_name:
                path = os.path.join(output_dir, out_file_name)
                if os.path.exists(path):
                    size_kb = os.path.getsize(path) / 1024
                    print(f"  {out_file_name}: {size_kb:.0f} KB")


if __name__ == "__main__":
    main()
