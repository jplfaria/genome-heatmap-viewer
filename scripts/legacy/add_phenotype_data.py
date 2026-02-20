#!/usr/bin/env python3
"""
Add growth phenotype data to tree_data.json
"""

import sqlite3
import json

def add_phenotype_data():
    # Load existing tree data
    with open('tree_data.json', 'r') as f:
        tree_data = json.load(f)

    # Connect to database
    conn = sqlite3.connect('berdl_tables.db')
    cursor = conn.cursor()

    # Get phenotype data for all genomes in the tree
    cursor.execute("""
        SELECT genome_id,
               positive_growth,
               negative_growth,
               true_positives,
               true_negatives,
               false_positives,
               false_negatives,
               accuracy
        FROM growth_phenotype_summary
    """)

    phenotype_data = {}
    for row in cursor.fetchall():
        genome_id, pos, neg, tp, tn, fp, fn, acc = row
        phenotype_data[genome_id] = {
            'positive_growth': pos,
            'negative_growth': neg,
            'true_positives': tp,
            'true_negatives': tn,
            'false_positives': fp,
            'false_negatives': fn,
            'accuracy': acc
        }

    conn.close()

    # Add phenotype data to genome_metadata
    for genome_id in tree_data['genome_ids']:
        if genome_id in phenotype_data:
            tree_data['genome_metadata'][genome_id]['phenotype'] = phenotype_data[genome_id]
        else:
            # No phenotype data available
            tree_data['genome_metadata'][genome_id]['phenotype'] = None

    # Save updated tree data
    with open('tree_data.json', 'w') as f:
        json.dump(tree_data, f)

    print(f"✓ Added phenotype data for {len(phenotype_data)} genomes")
    print(f"✓ Total genomes in tree: {len(tree_data['genome_ids'])}")

    # Show which genomes have data
    with_data = sum(1 for gid in tree_data['genome_ids'] if gid in phenotype_data)
    print(f"✓ Genomes with phenotype data: {with_data}/{len(tree_data['genome_ids'])}")

if __name__ == '__main__':
    add_phenotype_data()
