#!/usr/bin/env python3
"""
Extract reference genome statistics from pan_genome_features table.

This script extracts gene-level statistics for ALL genomes in the pangenome,
not just the user genome. This enables displaying stats in the Tree view
for reference genomes.

Output: ../data/ref_genomes_data.json with stats for all genomes
"""

import sqlite3
import json
import sys

def extract_pan_genome_features():
    """Extract statistics for all genomes from pan_genome_features table"""

    # Connect to database
    db_path = 'berdl_tables.db'
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as e:
        print(f"Error connecting to {db_path}: {e}")
        sys.exit(1)

    cursor = conn.cursor()

    # Load existing tree data to get genome IDs
    try:
        with open('../data/tree_data.json', 'r') as f:
            tree_data = json.load(f)
    except FileNotFoundError:
        print("Error: ../data/tree_data.json not found. Run generate_tree_data.py first.")
        sys.exit(1)

    genome_ids = tree_data['genome_ids']
    user_genome_id = tree_data['user_genome_id']

    print("Extracting pan_genome_features statistics...")
    print("=" * 60)
    print(f"Database: {db_path}")
    print(f"Genomes to process: {len(genome_ids)}")
    print(f"User genome: {user_genome_id}")
    print()

    ref_genomes_data = {
        'user_genome': user_genome_id,
        'n_genomes': len(genome_ids),
        'genomes': {}
    }

    for genome_id in genome_ids:
        print(f"Processing {genome_id}...")

        # Query all features for this genome
        cursor.execute("""
            SELECT
                feature_id,
                cluster_id,
                is_core,
                rast_function,
                bakta_function,
                ko,
                cog,
                pfam,
                go,
                ec
            FROM pan_genome_features
            WHERE genome_id = ?
        """, (genome_id,))

        rows = cursor.fetchall()

        if len(rows) == 0:
            print(f"  ⚠ No features found for {genome_id}")
            continue

        print(f"  Found {len(rows)} genes")

        # Compute statistics
        total_genes = len(rows)
        core_genes = 0
        accessory_genes = 0
        no_cluster = 0

        # Annotation coverage
        has_ko = 0
        has_ec = 0
        has_go = 0
        has_cog = 0
        has_pfam = 0
        has_function = 0
        hypothetical = 0

        for row in rows:
            (fid, cluster_id, is_core, rast_func, bakta_func, ko, cog, pfam, go, ec) = row

            # Pangenome classification
            if is_core == 1:
                core_genes += 1
            elif cluster_id is not None and cluster_id != '':
                accessory_genes += 1
            else:
                no_cluster += 1

            # Annotation coverage
            if ko and ko.strip(): has_ko += 1
            if ec and ec.strip(): has_ec += 1
            if go and go.strip(): has_go += 1
            if cog and cog.strip(): has_cog += 1
            if pfam and pfam.strip(): has_pfam += 1

            # Function annotation - check both RAST and Bakta
            # Use RAST if available, otherwise Bakta
            func = rast_func if rast_func and rast_func.strip() else bakta_func

            if func and func.strip():
                func_lower = func.lower()
                if 'hypothetical' in func_lower or 'uncharacterized' in func_lower:
                    hypothetical += 1
                else:
                    has_function += 1
            else:
                hypothetical += 1

        # Count missing core genes
        # Get total number of core clusters in the pangenome
        cursor.execute("""
            SELECT COUNT(DISTINCT cluster_id)
            FROM pan_genome_features
            WHERE is_core = 1 AND cluster_id IS NOT NULL AND cluster_id != ''
        """)
        total_core_clusters = cursor.fetchone()[0]

        missing_core = max(0, total_core_clusters - core_genes)

        # Get assembly stats (n_contigs, n_clusters)
        cursor.execute("""
            SELECT COUNT(DISTINCT cluster_id)
            FROM pan_genome_features
            WHERE genome_id = ? AND cluster_id IS NOT NULL AND cluster_id != ''
        """, (genome_id,))
        n_clusters = cursor.fetchone()[0]

        stats = {
            'n_genes': total_genes,
            'n_clusters': n_clusters,
            'core_genes': core_genes,
            'accessory_genes': accessory_genes,
            'no_cluster': no_cluster,
            'core_pct': round(core_genes / total_genes, 4) if total_genes > 0 else 0,
            'missing_core': missing_core,

            # Annotation coverage
            'has_ko': has_ko,
            'has_ec': has_ec,
            'has_go': has_go,
            'has_cog': has_cog,
            'has_pfam': has_pfam,
            'ko_pct': round(has_ko / total_genes, 3) if total_genes > 0 else 0,
            'ec_pct': round(has_ec / total_genes, 3) if total_genes > 0 else 0,
            'go_pct': round(has_go / total_genes, 3) if total_genes > 0 else 0,

            # Annotation quality
            'hypothetical': hypothetical,
            'has_function': has_function,
            'hypo_pct': round(hypothetical / total_genes, 3) if total_genes > 0 else 0,
        }

        ref_genomes_data['genomes'][genome_id] = stats

        print(f"  Stats: {core_genes} core, {accessory_genes} accessory, {missing_core} missing core")
        print(f"  Annotation: {has_function} characterized, {hypothetical} hypothetical ({hypothetical/total_genes*100:.1f}%)")

    conn.close()

    # Save to file
    output_file = '../data/ref_genomes_data.json'
    with open(output_file, 'w') as f:
        json.dump(ref_genomes_data, f, indent=2)

    print()
    print("=" * 60)
    print(f"✓ Saved {len(ref_genomes_data['genomes'])} genome stats to {output_file}")
    print()
    print("Stats computed:")
    print("  - n_genes, n_clusters")
    print("  - core_genes, accessory_genes, core_pct, missing_core")
    print("  - has_ko, has_ec, has_go, has_cog, has_pfam (counts and %)")
    print("  - hypothetical, has_function, hypo_pct")

if __name__ == '__main__':
    extract_pan_genome_features()
