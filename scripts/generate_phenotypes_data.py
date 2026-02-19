#!/usr/bin/env python3
"""Generate phenotype data for integration into ../data/genes_data.json.

Supports both old (berdl_tables.db) and new (GenomeDataLakeTables) schemas.

This script extracts phenotype statistics and adds two new fields to each gene:
- N_PHENOTYPES (index 36): Number of distinct phenotypes linked to this gene
- N_FITNESS (index 37): Number of phenotype associations with fitness data (fitness_match='yes')

The ESSENTIALITY field (index 35) is already computed in generate_genes_data.py.
"""

import json
import sqlite3
import sys
from collections import defaultdict

DB_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/berdl_tables.db"
GENES_DATA_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/../data/genes_data.json"


def detect_schema(conn):
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    return 'new' if 'user_feature' in tables else 'old'


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    genes_data_path = sys.argv[2] if len(sys.argv) > 2 else GENES_DATA_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    schema = detect_schema(conn)
    print(f"Detected schema: {schema}")
    print("Extracting phenotype statistics from database...")

    # --- Step 1: Identify user genome ---
    if schema == 'new':
        user_genome_row = conn.execute(
            "SELECT genome FROM genome WHERE kind = 'user' LIMIT 1"
        ).fetchone()
        if not user_genome_row:
            print("ERROR: No user genome found")
            sys.exit(1)
        user_genome_id = user_genome_row["genome"]
        phenotype_table = "gene_phenotype"
    else:
        user_genome_row = conn.execute(
            "SELECT id FROM genome WHERE id LIKE 'user_%' LIMIT 1"
        ).fetchone()
        if not user_genome_row:
            print("ERROR: No user genome found")
            sys.exit(1)
        user_genome_id = user_genome_row["id"]
        phenotype_table = "gene_phenotypes"

    print(f"  User genome: {user_genome_id}")

    # --- Step 2: Load existing ../data/genes_data.json ---
    print(f"Loading {genes_data_path}...")
    with open(genes_data_path, "r") as f:
        genes_data = json.load(f)

    print(f"  Loaded {len(genes_data)} genes with {len(genes_data[0])} fields each")

    # Build gene ID → array index mapping (use field index 1 = FID)
    gene_id_to_idx = {}
    for idx, gene in enumerate(genes_data):
        gene_id = gene[1]  # Field 1 = FID (feature ID)
        gene_id_to_idx[gene_id] = idx

    # --- Step 3: Count phenotypes per gene ---
    print("Counting phenotypes and fitness scores per gene...")

    phenotype_counts = defaultdict(set)  # gene_id -> set of phenotype_ids
    fitness_counts = defaultdict(int)    # gene_id -> count of fitness_match='yes'

    query = f"""
        SELECT gene_id, phenotype_id, fitness_match
        FROM {phenotype_table}
        WHERE genome_id = ?
    """

    for row in conn.execute(query, (user_genome_id,)):
        gene_id = row["gene_id"]
        phenotype_id = row["phenotype_id"]
        fitness_match = row["fitness_match"]

        phenotype_counts[gene_id].add(phenotype_id)

        if fitness_match and fitness_match.lower() == "yes":
            fitness_counts[gene_id] += 1

    conn.close()

    print(f"  Found phenotype data for {len(phenotype_counts)} genes")

    # --- Step 4: Add two new fields to each gene ---
    genes_with_phenotypes = 0
    genes_with_fitness = 0

    for idx, gene in enumerate(genes_data):
        gene_id = gene[1]  # FID

        n_phenotypes = len(phenotype_counts.get(gene_id, set()))
        n_fitness = fitness_counts.get(gene_id, 0)

        # Append new fields (indices 36 and 37)
        gene.append(n_phenotypes)
        gene.append(n_fitness)

        if n_phenotypes > 0:
            genes_with_phenotypes += 1
        if n_fitness > 0:
            genes_with_fitness += 1

    print(f"  {genes_with_phenotypes} genes have phenotype data")
    print(f"  {genes_with_fitness} genes have fitness scores")

    # --- Step 5: Write updated ../data/genes_data.json ---
    print(f"\nWriting updated {genes_data_path}...")
    with open(genes_data_path, "w") as f:
        json.dump(genes_data, f, separators=(",", ":"))

    size_kb = len(json.dumps(genes_data, separators=(",", ":"))) / 1024
    print(f"  {len(genes_data)} genes × {len(genes_data[0])} fields")
    print(f"  File size: {size_kb:.0f} KB")
    print("Done!")


if __name__ == "__main__":
    main()
