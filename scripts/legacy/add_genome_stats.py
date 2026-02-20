#!/usr/bin/env python3
"""
Add comprehensive genome-level statistics to tree_data.json

For the USER genome: compute from genes_data.json
For REFERENCE genomes: use existing metadata + contigs count

Stats added:
- Assembly: n_contigs (already exists)
- Pangenome: core_genes, accessory_genes, singleton_genes
- Annotation: hypothetical_count, hypo_pct, characterized_count
- Coverage: ko_pct, ec_pct, go_pct, cog_pct, pfam_pct
- Quality: avg_consistency, avg_specificity
- Metabolic: metabolic_genes, essential_genes (user only)
"""

import json

def add_genome_stats():
    # Load data files
    with open('tree_data.json', 'r') as f:
        tree_data = json.load(f)

    with open('genes_data.json', 'r') as f:
        user_genes = json.load(f)

    with open('reactions_data.json', 'r') as f:
        reactions_data = json.load(f)

    # Field indices
    F = {
        'CONS_FRAC': 5, 'PAN_CAT': 6, 'FUNC': 7,
        'N_KO': 8, 'N_COG': 9, 'N_PFAM': 10, 'N_GO': 11,
        'RAST_CONS': 13, 'KO_CONS': 14, 'GO_CONS': 15,
        'EC_CONS': 16, 'AVG_CONS': 17, 'BAKTA_CONS': 18,
        'SPECIFICITY': 20, 'IS_HYPO': 21, 'N_EC': 23
    }

    user_genome_id = reactions_data['user_genome']
    print(f"Computing stats for user genome: {user_genome_id}\n")

    # Compute user genome stats from genes_data.json
    total = len(user_genes)

    # Pangenome composition
    core = sum(1 for g in user_genes if g[F['PAN_CAT']] == 2)
    accessory = sum(1 for g in user_genes if g[F['PAN_CAT']] == 1)
    singleton = sum(1 for g in user_genes if g[F['CONS_FRAC']] is not None and g[F['CONS_FRAC']] < 0.05)
    no_cluster = sum(1 for g in user_genes if g[F['CONS_FRAC']] is None)

    print(f"Pangenome:")
    print(f"  Core: {core} ({core/total*100:.1f}%)")
    print(f"  Accessory: {accessory} ({accessory/total*100:.1f}%)")
    print(f"  Singleton: {singleton}")
    print(f"  No cluster: {no_cluster}")

    # Annotation completeness
    hypothetical = sum(1 for g in user_genes if g[F['IS_HYPO']] == 1)
    characterized = total - hypothetical

    print(f"\nAnnotation:")
    print(f"  Hypothetical: {hypothetical} ({hypothetical/total*100:.1f}%)")
    print(f"  Characterized: {characterized}")

    # Functional coverage
    has_ko = sum(1 for g in user_genes if g[F['N_KO']] > 0)
    has_ec = sum(1 for g in user_genes if g[F['N_EC']] > 0)
    has_go = sum(1 for g in user_genes if g[F['N_GO']] > 0)
    has_cog = sum(1 for g in user_genes if g[F['N_COG']] > 0)
    has_pfam = sum(1 for g in user_genes if g[F['N_PFAM']] > 0)

    print(f"\nFunctional Coverage:")
    print(f"  KO: {has_ko} ({has_ko/total*100:.1f}%)")
    print(f"  EC: {has_ec} ({has_ec/total*100:.1f}%)")
    print(f"  GO: {has_go} ({has_go/total*100:.1f}%)")
    print(f"  COG: {has_cog} ({has_cog/total*100:.1f}%)")
    print(f"  Pfam: {has_pfam} ({has_pfam/total*100:.1f}%)")

    # Quality metrics
    cons_values = [g[F['AVG_CONS']] for g in user_genes if g[F['AVG_CONS']] >= 0]
    avg_cons = sum(cons_values) / len(cons_values) if cons_values else 0
    low_cons = sum(1 for c in cons_values if c < 0.5)
    high_cons = sum(1 for c in cons_values if c >= 0.8)

    spec_values = [g[F['SPECIFICITY']] for g in user_genes if g[F['SPECIFICITY']] >= 0]
    avg_spec = sum(spec_values) / len(spec_values) if spec_values else 0
    high_spec = sum(1 for s in spec_values if s >= 0.7)

    print(f"\nQuality:")
    print(f"  Avg Consistency: {avg_cons:.3f}")
    print(f"  Low Consistency (<0.5): {low_cons}")
    print(f"  High Consistency (≥0.8): {high_cons}")
    print(f"  Avg Specificity: {avg_spec:.3f}")
    print(f"  High Specificity (≥0.7): {high_spec}")

    # Metabolic genes
    metabolic_genes = len(reactions_data.get('gene_index', {}))
    essential_genes = 0

    # Count genes with essential reactions
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

    print(f"\nMetabolic:")
    print(f"  Metabolic genes: {metabolic_genes}")
    print(f"  Essential metabolic: {essential_genes}")

    # Add stats to user genome
    if user_genome_id in tree_data['genome_metadata']:
        tree_data['genome_metadata'][user_genome_id]['stats'] = {
            'core_genes': core,
            'accessory_genes': accessory,
            'singleton_genes': singleton,
            'no_cluster': no_cluster,
            'hypothetical': hypothetical,
            'characterized': characterized,
            'hypo_pct': round(hypothetical/total*100, 1),
            'ko_pct': round(has_ko/total*100, 1),
            'ec_pct': round(has_ec/total*100, 1),
            'go_pct': round(has_go/total*100, 1),
            'cog_pct': round(has_cog/total*100, 1),
            'pfam_pct': round(has_pfam/total*100, 1),
            'avg_consistency': round(avg_cons, 3),
            'low_consistency': low_cons,
            'high_consistency': high_cons,
            'avg_specificity': round(avg_spec, 3),
            'high_specificity': high_spec,
            'metabolic_genes': metabolic_genes,
            'essential_metabolic': essential_genes,
        }

    # For reference genomes, add minimal stats (just contigs, which already exists)
    for genome_id in tree_data['genome_ids']:
        if genome_id != user_genome_id:
            if genome_id in tree_data['genome_metadata']:
                # Add empty stats object for consistency
                tree_data['genome_metadata'][genome_id]['stats'] = {
                    # Only n_contigs available from existing metadata
                    # Other stats would require per-genome gene data
                }

    # Save
    with open('tree_data.json', 'w') as f:
        json.dump(tree_data, f, indent=2)

    print(f"\n{'='*60}")
    print(f"✓ Added comprehensive stats to user genome")
    print(f"✓ Updated tree_data.json")

if __name__ == '__main__':
    add_genome_stats()
