#!/usr/bin/env python3
"""Generate phenotype data for integration into genes_data.json.

Extracts phenotype statistics from the gene_phenotype table and adds
five new fields to each gene:
- N_PHENOTYPES (index 37): Number of distinct phenotypes linked to this gene
- N_FITNESS (index 38): Number of phenotype associations with fitness scores
- FITNESS_AVG (index 39): Average fitness score across all scored phenotypes (-1 if none)
- N_FITNESS_AGREE (index 40): Count of conditions where model and fitness agree
- FITNESS_AGREE_PCT (index 41): Agreement fraction (0.0-1.0), -1 if no scored conditions

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

    # Count phenotypes, fitness scores, and model-fitness agreement per gene
    print("Counting phenotypes, fitness scores, and model-fitness agreement per gene...")

    phenotype_counts = defaultdict(set)
    fitness_counts = defaultdict(int)
    fitness_avg_sum = defaultdict(float)
    fitness_avg_count = defaultdict(int)
    fitness_agree = defaultdict(int)      # conditions where model and fitness agree
    fitness_scored = defaultdict(int)     # total scored conditions

    for row in conn.execute("""
        SELECT gene_id, phenotype_id, fitness_match, fitness_avg, essentiality_fraction
        FROM gene_phenotype
        WHERE genome_id = ?
    """, (user_genome_id,)):
        gene_id = row["gene_id"]
        phenotype_counts[gene_id].add(row["phenotype_id"])
        if row["fitness_match"] == "has_score":
            fitness_counts[gene_id] += 1
            if row["fitness_avg"] is not None:
                fitness_avg_sum[gene_id] += row["fitness_avg"]
                fitness_avg_count[gene_id] += 1
            # Model-fitness agreement: model says essential if essentiality_fraction > 0
            # Fitness says harmful if fitness_avg < 0
            # Agreement: both essential OR both not essential
            fitness_scored[gene_id] += 1
            model_essential = (row["essentiality_fraction"] or 0) > 0
            fitness_harmful = (row["fitness_avg"] or 0) < 0
            if model_essential == fitness_harmful:
                fitness_agree[gene_id] += 1

    conn.close()

    print(f"  Found phenotype data for {len(phenotype_counts)} genes")
    print(f"  Found fitness scores for {len(fitness_counts)} genes")

    # Add five new fields to each gene
    genes_with_phenotypes = 0
    genes_with_fitness = 0
    genes_with_agreement = 0

    for gene in genes_data:
        gene_id = gene[1]  # FID
        n_phenotypes = len(phenotype_counts.get(gene_id, set()))
        n_fitness = fitness_counts.get(gene_id, 0)

        if fitness_avg_count.get(gene_id, 0) > 0:
            avg_fitness = round(fitness_avg_sum[gene_id] / fitness_avg_count[gene_id], 4)
        else:
            avg_fitness = -1  # N/A sentinel

        # Model-fitness agreement
        n_agree = fitness_agree.get(gene_id, 0)
        n_scored = fitness_scored.get(gene_id, 0)
        agree_pct = round(n_agree / n_scored, 4) if n_scored > 0 else -1

        gene.append(n_phenotypes)   # [37] N_PHENOTYPES
        gene.append(n_fitness)      # [38] N_FITNESS
        gene.append(avg_fitness)    # [39] FITNESS_AVG
        gene.append(n_agree)        # [40] N_FITNESS_AGREE
        gene.append(agree_pct)      # [41] FITNESS_AGREE_PCT

        if n_phenotypes > 0:
            genes_with_phenotypes += 1
        if n_fitness > 0:
            genes_with_fitness += 1
        if n_scored > 0:
            genes_with_agreement += 1

    print(f"  {genes_with_phenotypes} genes have phenotype data")
    print(f"  {genes_with_fitness} genes have fitness scores")
    print(f"  {genes_with_agreement} genes have model-fitness agreement data")

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
