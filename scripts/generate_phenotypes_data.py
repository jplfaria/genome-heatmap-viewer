#!/usr/bin/env python3
"""Generate phenotype data for integration into genes_data.json.

Extracts phenotype statistics from the gene_phenotype table and adds
two new fields to each gene:
- N_PHENOTYPES (index 36): Number of distinct phenotypes linked to this gene
- N_FITNESS (index 37): Number of phenotype associations with fitness_match='yes'

Usage:
    python3 generate_phenotypes_data.py DB_PATH GENES_DATA_PATH
"""

import json
import sqlite3
import sys
from collections import defaultdict


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 generate_phenotypes_data.py DB_PATH GENES_DATA_PATH")
        sys.exit(1)

    db_path = sys.argv[1]
    genes_data_path = sys.argv[2]

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    print("Extracting phenotype statistics from database...")

    # Identify user genome
    user_genome_row = conn.execute(
        "SELECT genome FROM genome WHERE kind = 'user' LIMIT 1"
    ).fetchone()
    if not user_genome_row:
        print("ERROR: No user genome found")
        sys.exit(1)
    user_genome_id = user_genome_row["genome"]
    print(f"  User genome: {user_genome_id}")

    # Load existing genes_data.json
    print(f"Loading {genes_data_path}...")
    with open(genes_data_path, "r") as f:
        genes_data = json.load(f)

    print(f"  Loaded {len(genes_data)} genes with {len(genes_data[0])} fields each")

    # Count phenotypes per gene
    print("Counting phenotypes and fitness scores per gene...")

    phenotype_counts = defaultdict(set)
    fitness_counts = defaultdict(int)

    for row in conn.execute("""
        SELECT gene_id, phenotype_id, fitness_match
        FROM gene_phenotype
        WHERE genome_id = ?
    """, (user_genome_id,)):
        gene_id = row["gene_id"]
        phenotype_counts[gene_id].add(row["phenotype_id"])
        if row["fitness_match"] and row["fitness_match"].lower() == "yes":
            fitness_counts[gene_id] += 1

    conn.close()

    print(f"  Found phenotype data for {len(phenotype_counts)} genes")

    # Add two new fields to each gene
    genes_with_phenotypes = 0
    genes_with_fitness = 0

    for gene in genes_data:
        gene_id = gene[1]  # FID
        n_phenotypes = len(phenotype_counts.get(gene_id, set()))
        n_fitness = fitness_counts.get(gene_id, 0)

        gene.append(n_phenotypes)
        gene.append(n_fitness)

        if n_phenotypes > 0:
            genes_with_phenotypes += 1
        if n_fitness > 0:
            genes_with_fitness += 1

    print(f"  {genes_with_phenotypes} genes have phenotype data")
    print(f"  {genes_with_fitness} genes have fitness scores")

    # Write updated genes_data.json
    print(f"\nWriting updated {genes_data_path}...")
    with open(genes_data_path, "w") as f:
        json.dump(genes_data, f, separators=(",", ":"))

    size_kb = len(json.dumps(genes_data, separators=(",", ":"))) / 1024
    print(f"  {len(genes_data)} genes x {len(genes_data[0])} fields")
    print(f"  File size: {size_kb:.0f} KB")
    print("Done!")


if __name__ == "__main__":
    main()
