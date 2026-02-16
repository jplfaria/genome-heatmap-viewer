#!/usr/bin/env python3
"""
Validate genes_data.json against SQLite database.

Cross-checks 10 random genes to ensure data extraction is correct.
Verifies conservation, consistency, annotation counts, and multi-cluster handling.
"""

import json
import sqlite3
import random
import sys
from pathlib import Path


def query_conservation(cursor, cluster_id, ref_genome_count):
    """
    Calculate conservation fraction for a cluster.
    Conservation = (# ref genomes with this cluster) / total ref genomes
    """
    if not cluster_id or cluster_id == '':
        return None

    # Handle multi-cluster genes (semicolon-separated)
    cluster_ids = [c.strip() for c in cluster_id.split(';') if c.strip()]

    # For multi-cluster genes, take MAX conservation (as per Chris Henry)
    max_conservation = 0.0
    for cid in cluster_ids:
        count = cursor.execute("""
            SELECT COUNT(DISTINCT genome_id)
            FROM pan_genome_features
            WHERE cluster_id = ?
        """, (cid,)).fetchone()[0]

        conservation = count / ref_genome_count if ref_genome_count > 0 else 0
        max_conservation = max(max_conservation, conservation)

    return round(max_conservation, 4)


def count_terms(value):
    """Count semicolon-separated terms in a field."""
    if not value or value == '':
        return 0
    return len([term for term in value.split(';') if term.strip()])


def validate_gene(gene, db_row, ref_genomes_count, field_indices):
    """
    Cross-check a single gene against database row.
    Returns list of error messages (empty if all checks pass).
    """
    errors = []
    F = field_indices

    # 1. Conservation fraction validation
    cluster_id = db_row['pangenome_cluster_id']
    if cluster_id and cluster_id.strip():
        actual_cons = query_conservation(cursor, cluster_id, ref_genomes_count)
        expected_cons = gene[F['CONS_FRAC']]

        if actual_cons is not None and expected_cons is not None:
            if abs(actual_cons - expected_cons) > 0.01:
                errors.append(f"Conservation: DB={actual_cons:.4f} vs JSON={expected_cons:.4f}")

    # 2. Annotation counts validation
    counts_to_check = [
        ('ko', 'N_KO'),
        ('cog', 'N_COG'),
        ('pfam', 'N_PFAM'),
        ('go', 'N_GO'),
        ('ec', 'N_EC'),
    ]

    for db_field, json_field in counts_to_check:
        n_db = count_terms(db_row[db_field])
        n_json = gene[F[json_field]]
        if n_db != n_json:
            errors.append(f"{json_field}: DB={n_db} vs JSON={n_json}")

    # 3. Protein length validation
    if db_row['length'] != gene[F['PROT_LEN']]:
        errors.append(f"Protein length: DB={db_row['length']} vs JSON={gene[F['PROT_LEN']]}")

    # 4. Start position validation
    if db_row['start'] != gene[F['START']]:
        errors.append(f"Start: DB={db_row['start']} vs JSON={gene[F['START']]}")

    # 5. Strand validation (1=forward, 0=reverse)
    expected_strand = 1 if db_row['strand'] == '+' else 0
    if expected_strand != gene[F['STRAND']]:
        errors.append(f"Strand: DB={db_row['strand']} vs JSON={gene[F['STRAND']]}")

    # 6. Field range validation
    cons_frac = gene[F['CONS_FRAC']]
    if cons_frac is not None and (cons_frac < 0.0 or cons_frac > 1.0):
        errors.append(f"Conservation out of range: {cons_frac}")

    avg_cons = gene[F['AVG_CONS']]
    if avg_cons is not None and avg_cons != -1 and (avg_cons < 0.0 or avg_cons > 1.0):
        errors.append(f"Avg consistency out of range: {avg_cons}")

    prot_len = gene[F['PROT_LEN']]
    if prot_len < 20 or prot_len > 5000:
        errors.append(f"Protein length unusual: {prot_len} aa")

    return errors


def main():
    # Load config to get field indices
    try:
        with open('config.json') as f:
            config = json.load(f)
        field_indices = config['fields']
    except FileNotFoundError:
        print("ERROR: config.json not found")
        sys.exit(1)

    # Load genes_data.json
    try:
        with open('genes_data.json') as f:
            genes = json.load(f)
        print(f"✓ Loaded {len(genes)} genes from genes_data.json")
    except FileNotFoundError:
        print("ERROR: genes_data.json not found")
        sys.exit(1)

    # Load metadata to get reference genome count
    try:
        with open('metadata.json') as f:
            metadata = json.load(f)
        ref_genome_count = metadata.get('n_ref_genomes', 13)
        print(f"✓ Reference genomes: {ref_genome_count}")
    except FileNotFoundError:
        print("WARNING: metadata.json not found, assuming 13 reference genomes")
        ref_genome_count = 13

    # Connect to database
    db_path = 'berdl_tables.db'
    if not Path(db_path).exists():
        print(f"ERROR: {db_path} not found")
        sys.exit(1)

    try:
        global cursor  # Make cursor global for query_conservation
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        print(f"✓ Connected to {db_path}")
    except sqlite3.Error as e:
        print(f"ERROR: Failed to connect to database: {e}")
        sys.exit(1)

    print()
    print("=" * 60)
    print("VALIDATING 10 RANDOM GENES")
    print("=" * 60)

    # Sample 10 random genes
    sample_size = min(10, len(genes))
    sample_indices = random.sample(range(len(genes)), sample_size)

    all_errors = []
    genes_with_errors = 0

    for idx in sample_indices:
        gene = genes[idx]
        fid = gene[field_indices['FID']]
        func = gene[field_indices['FUNC']]

        # Query database for this gene
        row = cursor.execute("""
            SELECT * FROM genome_features
            WHERE feature_id = ?
        """, (fid,)).fetchone()

        if not row:
            print(f"❌ Gene {fid} NOT FOUND in database")
            genes_with_errors += 1
            all_errors.append(f"Gene {fid} missing from database")
            continue

        # Validate this gene
        errors = validate_gene(gene, row, ref_genome_count, field_indices)

        if errors:
            print(f"\n❌ Gene {fid}")
            print(f"   Function: {func[:60]}...")
            for error in errors:
                print(f"   - {error}")
            genes_with_errors += 1
            all_errors.extend([f"{fid}: {e}" for e in errors])
        else:
            print(f"✓ Gene {fid}")

    conn.close()

    # Summary
    print()
    print("=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Genes validated: {sample_size}")
    print(f"Genes with errors: {genes_with_errors}")
    print(f"Total errors found: {len(all_errors)}")

    if genes_with_errors == 0:
        print()
        print("✅ ALL GENES VALIDATED SUCCESSFULLY!")
        print("   Data extraction appears correct.")
        return 0
    else:
        print()
        print(f"⚠️  {genes_with_errors}/{sample_size} genes have discrepancies")
        print("   Review errors above and check data extraction scripts.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
