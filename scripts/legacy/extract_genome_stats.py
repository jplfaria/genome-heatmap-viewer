#!/usr/bin/env python3
"""
Extract comprehensive genome-level statistics for tree visualization.

For each genome in the pangenome, compute:
1. Assembly quality metrics (contigs, total features)
2. Annotation completeness (hypothetical %, specificity)
3. Pangenome composition (core, accessory, singleton counts)
4. Metabolic capability (reactions, essential reactions)
5. Functional annotation depth (EC, KO, GO, etc.)
6. Annotation consistency (average across sources)

Output: Updates ../data/tree_data.json with new genome_stats fields

NOTE: This script computes per-genome statistics from ../data/genes_data.json
which only contains the USER genome's genes. For reference genomes, we'll
use aggregate statistics from the database pan_genome_features table.
"""

import sqlite3
import json
import sys

def extract_genome_stats():
    """Extract comprehensive statistics for all genomes"""

    # Load existing tree data
    with open('../data/tree_data.json', 'r') as f:
        tree_data = json.load(f)

    # Load user genome genes data
    with open('../data/genes_data.json', 'r') as f:
        user_genes = json.load(f)

    # Load reactions data for metabolic stats
    with open('../data/reactions_data.json', 'r') as f:
        reactions_data = json.load(f)

    # Connect to database for reference genome stats
    conn = sqlite3.connect('berdl_tables.db')
    cursor = conn.cursor()

    print("Extracting genome-level statistics...")
    print("=" * 60)

    genome_ids = tree_data['genome_ids']
    user_genome_id = reactions_data.get('user_genome')

    # Field indices from ../data/genes_data.json (matching our extraction script)
    F = {
        'ID': 0, 'FID': 1, 'LENGTH': 2, 'START': 3, 'STRAND': 4,
        'CONS_FRAC': 5, 'PAN_CAT': 6, 'FUNC': 7,
        'N_KO': 8, 'N_COG': 9, 'N_PFAM': 10, 'N_GO': 11,
        'LOC': 12, 'RAST_CONS': 13, 'KO_CONS': 14, 'GO_CONS': 15,
        'EC_CONS': 16, 'AVG_CONS': 17, 'BAKTA_CONS': 18,
        'EC_AVG_CONS': 19, 'SPECIFICITY': 20, 'IS_HYPO': 21,
        'HAS_NAME': 22, 'N_EC': 23, 'AGREEMENT': 24,
        'CLUSTER_SIZE': 25, 'N_MODULES': 26, 'EC_MAP_CONS': 27,
        'PROT_LEN': 28, 'N_PHENOTYPES': 29, 'N_FITNESS': 30
    }

    for genome_id in genome_ids:
        print(f"\n{genome_id}:")

        # For user genome, use ../data/genes_data.json
        if genome_id == user_genome_id:
            genes = user_genes
            total_genes = len(genes)
        else:
            # For reference genomes, get from database
            cursor.execute("""
                SELECT COUNT(*) FROM pan_genome_features
                WHERE genome_id = ?
            """, (genome_id,))
            total_genes = cursor.fetchone()[0]

            if total_genes == 0:
                print(f"  ⚠ No genes found")
                continue

            # Get aggregate stats from database
            # We'll compute what we can from pan_genome_features
            print(f"  (Reference genome - limited stats available)")
            genes = None

        # 1. PANGENOME COMPOSITION
        core_genes = sum(1 for g in genes if g[2] == 1)  # is_core = 1
        accessory_genes = sum(1 for g in genes if g[2] == 0 and g[3] is not None and g[3] >= 0.05)
        singleton_genes = sum(1 for g in genes if g[3] is not None and g[3] < 0.05)
        no_cluster = sum(1 for g in genes if g[3] is None)

        core_pct = (core_genes / total_genes * 100) if total_genes > 0 else 0
        accessory_pct = (accessory_genes / total_genes * 100) if total_genes > 0 else 0

        print(f"  Core: {core_genes} ({core_pct:.1f}%)")
        print(f"  Accessory: {accessory_genes} ({accessory_pct:.1f}%)")
        print(f"  Singleton: {singleton_genes}")
        print(f"  No cluster: {no_cluster}")

        # 2. ANNOTATION COMPLETENESS
        hypothetical = sum(1 for g in genes if g[4] and ('hypothetical' in g[4].lower() or
                                                          'uncharacterized' in g[4].lower() or
                                                          g[4].strip() == ''))
        has_function = total_genes - hypothetical
        hypo_pct = (hypothetical / total_genes * 100) if total_genes > 0 else 0

        print(f"  Hypothetical: {hypothetical} ({hypo_pct:.1f}%)")
        print(f"  Characterized: {has_function}")

        # 3. FUNCTIONAL ANNOTATION DEPTH
        has_ko = sum(1 for g in genes if g[5] and g[5].strip())
        has_ec = sum(1 for g in genes if g[6] and g[6].strip())
        has_go = sum(1 for g in genes if g[7] and g[7].strip())
        has_cog = sum(1 for g in genes if g[8] and g[8].strip())
        has_pfam = sum(1 for g in genes if g[9] and g[9].strip())

        print(f"  With KO: {has_ko} ({has_ko/total_genes*100:.1f}%)")
        print(f"  With EC: {has_ec} ({has_ec/total_genes*100:.1f}%)")
        print(f"  With GO: {has_go} ({has_go/total_genes*100:.1f}%)")
        print(f"  With COG: {has_cog} ({has_cog/total_genes*100:.1f}%)")
        print(f"  With Pfam: {has_pfam} ({has_pfam/total_genes*100:.1f}%)")

        # 4. ANNOTATION CONSISTENCY
        cons_values = []
        for g in genes:
            # Collect all consistency scores (rast, ko, bakta, ec, go)
            for cons in [g[10], g[11], g[12], g[13], g[14]]:
                if cons is not None and cons >= 0:
                    cons_values.append(cons)

        avg_consistency = sum(cons_values) / len(cons_values) if cons_values else 0
        low_consistency = sum(1 for c in cons_values if c < 0.5)
        high_consistency = sum(1 for c in cons_values if c >= 0.8)

        print(f"  Avg consistency: {avg_consistency:.3f}")
        print(f"  Low consistency (<0.5): {low_consistency}")
        print(f"  High consistency (≥0.8): {high_consistency}")

        # 5. ANNOTATION SPECIFICITY
        spec_values = [g[15] for g in genes if g[15] is not None and g[15] >= 0]
        avg_specificity = sum(spec_values) / len(spec_values) if spec_values else 0
        high_spec = sum(1 for s in spec_values if s >= 0.7)

        print(f"  Avg specificity: {avg_specificity:.3f}")
        print(f"  High specificity (≥0.7): {high_spec}")

        # 6. METABOLIC GENES (from reactions data)
        # Note: This is for user genome only since reactions are only for user
        metabolic_genes = 0
        essential_genes = 0
        if genome_id == reactions_data.get('user_genome'):
            metabolic_genes = len(reactions_data.get('gene_index', {}))

            # Count essential genes (those with essential_forward or essential_reverse)
            for gene_id, rxn_indices in reactions_data.get('gene_index', {}).items():
                rxns = reactions_data['reactions']
                rxn_ids = list(rxns.keys())
                for idx in rxn_indices:
                    if idx < len(rxn_ids):
                        rxn = rxns[rxn_ids[idx]]
                        if ('essential' in rxn.get('class_rich', '') or
                            'essential' in rxn.get('class_min', '')):
                            essential_genes += 1
                            break

            print(f"  Metabolic genes: {metabolic_genes}")
            print(f"  Essential metabolic: {essential_genes}")

        # Store in tree_data
        if genome_id not in tree_data['genome_metadata']:
            tree_data['genome_metadata'][genome_id] = {}

        tree_data['genome_metadata'][genome_id]['stats'] = {
            # Pangenome composition
            'core_genes': core_genes,
            'accessory_genes': accessory_genes,
            'singleton_genes': singleton_genes,
            'no_cluster': no_cluster,
            'core_pct': round(core_pct, 2),
            'accessory_pct': round(accessory_pct, 2),

            # Annotation completeness
            'hypothetical': hypothetical,
            'characterized': has_function,
            'hypo_pct': round(hypo_pct, 2),

            # Functional annotation depth
            'has_ko': has_ko,
            'has_ec': has_ec,
            'has_go': has_go,
            'has_cog': has_cog,
            'has_pfam': has_pfam,
            'ko_pct': round(has_ko/total_genes*100, 1),
            'ec_pct': round(has_ec/total_genes*100, 1),
            'go_pct': round(has_go/total_genes*100, 1),

            # Annotation quality
            'avg_consistency': round(avg_consistency, 3),
            'low_consistency': low_consistency,
            'high_consistency': high_consistency,
            'avg_specificity': round(avg_specificity, 3),
            'high_specificity': high_spec,

            # Metabolic (user genome only)
            'metabolic_genes': metabolic_genes,
            'essential_metabolic': essential_genes,
        }

    conn.close()

    # Save updated tree data
    with open('../data/tree_data.json', 'w') as f:
        json.dump(tree_data, f, indent=2)

    print("\n" + "=" * 60)
    print(f"✓ Updated ../data/tree_data.json with stats for {len(genome_ids)} genomes")
    print("\nNew stats fields:")
    print("  - Pangenome: core_genes, accessory_genes, singleton_genes")
    print("  - Annotation: hypothetical, characterized, hypo_pct")
    print("  - Coverage: has_ko, has_ec, has_go, etc.")
    print("  - Quality: avg_consistency, avg_specificity")
    print("  - Metabolic: metabolic_genes, essential_metabolic (user only)")

if __name__ == '__main__':
    extract_genome_stats()
