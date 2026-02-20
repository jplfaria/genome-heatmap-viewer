#!/usr/bin/env python3
"""
Create reference_phenotypes.json from Chris's experimental phenotype DB.

This is a ONE-TIME script. The output file is static and bundled with the viewer.
It contains 559 experimental genomes with accuracy data and P/N vectors for
computing Jaccard similarity against user genomes.

Usage:
    python scripts/create_reference_phenotypes.py \
        --db "/path/to/berdl_tables (3).db" \
        --output data/reference_phenotypes.json
"""

import argparse
import json
import sqlite3
import sys


def main():
    parser = argparse.ArgumentParser(description="Extract reference phenotypes for Jaccard comparison")
    parser.add_argument("--db", required=True, help="Path to Chris's reference DB with experimental phenotypes")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    # Get sorted phenotype IDs (shared across all genomes)
    phenotype_ids = [
        row[0] for row in conn.execute(
            "SELECT DISTINCT phenotype_id FROM growth_phenotypes_detailed "
            "WHERE source = 'experiment' ORDER BY phenotype_id"
        )
    ]
    print(f"Found {len(phenotype_ids)} phenotype IDs")

    # Get experimental genomes with accuracy
    summaries = conn.execute(
        "SELECT genome_id, accuracy FROM growth_phenotype_summary WHERE source = 'experiment'"
    ).fetchall()
    print(f"Found {len(summaries)} experimental genomes")

    # Build P/N vectors from detailed table
    # CP/FP/P → predicted positive (1), CN/FN/N → predicted negative (0)
    positive_classes = {'CP', 'FP', 'P'}

    # Load all experimental detailed rows at once for efficiency
    detailed = conn.execute(
        "SELECT genome_id, phenotype_id, class FROM growth_phenotypes_detailed "
        "WHERE source = 'experiment'"
    ).fetchall()

    # Build genome -> phenotype -> predicted_positive map
    genome_pheno = {}
    for row in detailed:
        gid = row["genome_id"]
        pid = row["phenotype_id"]
        if gid not in genome_pheno:
            genome_pheno[gid] = {}
        genome_pheno[gid][pid] = 1 if row["class"] in positive_classes else 0

    print(f"Built vectors for {len(genome_pheno)} genomes")

    # Build output
    genomes = []
    pid_index = {pid: i for i, pid in enumerate(phenotype_ids)}

    for row in summaries:
        gid = row["genome_id"]
        accuracy = row["accuracy"]
        pheno_map = genome_pheno.get(gid, {})

        # Build vector in phenotype_ids order
        vector = [pheno_map.get(pid, 0) for pid in phenotype_ids]

        genomes.append({
            "id": gid,
            "accuracy": round(accuracy, 4) if accuracy else None,
            "vector": vector
        })

    output = {
        "phenotype_ids": phenotype_ids,
        "n_genomes": len(genomes),
        "n_phenotypes": len(phenotype_ids),
        "genomes": genomes
    }

    with open(args.output, 'w') as f:
        json.dump(output, f, separators=(',', ':'))

    file_size = len(json.dumps(output, separators=(',', ':')))
    print(f"Written {args.output} ({file_size / 1024:.0f} KB)")
    print(f"  {len(genomes)} genomes, {len(phenotype_ids)} phenotypes")
    print(f"  {sum(1 for g in genomes if g['accuracy'] and g['accuracy'] > 0)} with accuracy > 0")

    conn.close()


if __name__ == "__main__":
    main()
