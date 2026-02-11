#!/usr/bin/env python3
"""Generate tree_data.json for the Genome Heatmap Viewer dendrogram.

Computes Jaccard distances on pangenome cluster presence/absence across
36 genomes (35 references + user genome), runs UPGMA hierarchical
clustering, and collects genome metadata.
"""

import json
import sqlite3
import sys

import numpy as np
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.spatial.distance import pdist, squareform

DB_PATH = "/Users/jplfaria/Downloads/berdl_tables_ontology_terms.db"
OUTPUT_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/tree_data.json"
USER_GENOME_DB_ID = "user_genome"      # ID in genome table
USER_GENOME_DISPLAY_ID = "562.61143"   # ID in genome_features table


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # --- Step 1: Build cluster sets per genome ---
    print("Loading reference genome clusters from pan_genome_features...")
    cur = conn.execute("SELECT genome_id, cluster_id FROM pan_genome_features")
    ref_clusters = {}
    for row in cur:
        gid = row["genome_id"]
        cid = row["cluster_id"]
        if gid not in ref_clusters:
            ref_clusters[gid] = set()
        ref_clusters[gid].add(cid)

    print(f"  {len(ref_clusters)} reference genomes loaded")

    print("Loading user genome clusters from genome_features...")
    cur = conn.execute(
        "SELECT pangenome_cluster_id FROM genome_features "
        "WHERE genome_id = ? AND pangenome_cluster_id IS NOT NULL",
        (USER_GENOME_DISPLAY_ID,),
    )
    user_clusters = set()
    for row in cur:
        for cid in row["pangenome_cluster_id"].split(";"):
            cid = cid.strip()
            if cid:
                user_clusters.add(cid)
    print(f"  User genome has {len(user_clusters)} clusters")

    # Combine: user genome first, then references sorted
    all_clusters_by_genome = {USER_GENOME_DISPLAY_ID: user_clusters}
    for gid in sorted(ref_clusters.keys()):
        all_clusters_by_genome[gid] = ref_clusters[gid]

    genome_ids = list(all_clusters_by_genome.keys())
    n_genomes = len(genome_ids)
    print(f"Total genomes: {n_genomes}")

    # --- Step 2: Build binary presence/absence matrix ---
    all_cluster_ids = set()
    for clusters in all_clusters_by_genome.values():
        all_cluster_ids.update(clusters)
    all_cluster_ids = sorted(all_cluster_ids)
    cluster_to_idx = {cid: i for i, cid in enumerate(all_cluster_ids)}
    n_clusters = len(all_cluster_ids)
    print(f"Total unique clusters: {n_clusters}")

    matrix = np.zeros((n_genomes, n_clusters), dtype=np.uint8)
    for gi, gid in enumerate(genome_ids):
        for cid in all_clusters_by_genome[gid]:
            matrix[gi, cluster_to_idx[cid]] = 1

    # --- Step 3: Compute pairwise Jaccard distances ---
    print("Computing Jaccard distance matrix...")
    condensed = pdist(matrix, metric="jaccard")
    dist_matrix = squareform(condensed)
    print(f"  Distance range: {condensed.min():.4f} - {condensed.max():.4f}")

    # --- Step 4: UPGMA hierarchical clustering ---
    print("Running UPGMA clustering...")
    Z = linkage(condensed, method="average")
    leaf_order_indices = leaves_list(Z)
    leaf_order = [genome_ids[i] for i in leaf_order_indices]

    # --- Step 5: Genome metadata ---
    print("Loading genome metadata...")
    metadata = {}

    # From genome table (uses 'user_genome' as ID)
    cur = conn.execute(
        "SELECT id, gtdb_taxonomy, ncbi_taxonomy, n_contigs, n_features FROM genome"
    )
    genome_table = {}
    for row in cur:
        genome_table[row["id"]] = dict(row)

    # Map user_genome -> display ID
    for gid in genome_ids:
        db_id = USER_GENOME_DB_ID if gid == USER_GENOME_DISPLAY_ID else gid
        row = genome_table.get(db_id, {})
        tax_str = row.get("gtdb_taxonomy", "") or ""
        tax = {}
        if tax_str:
            for part in tax_str.split(";"):
                part = part.strip()
                if part.startswith("d__"):
                    tax["domain"] = part[3:]
                elif part.startswith("p__"):
                    tax["phylum"] = part[3:]
                elif part.startswith("c__"):
                    tax["class"] = part[3:]
                elif part.startswith("o__"):
                    tax["order"] = part[3:]
                elif part.startswith("f__"):
                    tax["family"] = part[3:]
                elif part.startswith("g__"):
                    tax["genus"] = part[3:]
                elif part.startswith("s__"):
                    tax["species"] = part[3:]

        metadata[gid] = {
            "tax": tax,
            "n_features": row.get("n_features"),
            "n_contigs": row.get("n_contigs"),
            "ani_to_user": None,
        }

    # ANI data
    print("Loading ANI data...")
    cur = conn.execute("SELECT genome1, genome2, ani FROM genome_ani")
    for row in cur:
        g2 = row["genome2"]
        if g2 in metadata:
            metadata[g2]["ani_to_user"] = round(row["ani"], 2)

    # --- Step 6: Per-genome aggregate stats ---
    print("Computing per-genome stats...")
    genome_stats = {}

    # For reference genomes: count features and core/accessory from pan_genome_features
    for gid in genome_ids:
        if gid == USER_GENOME_DISPLAY_ID:
            continue
        clusters = ref_clusters[gid]
        # Count core clusters (is_core = 1)
        cur = conn.execute(
            "SELECT COUNT(DISTINCT cluster_id) FROM pan_genome_features "
            "WHERE genome_id = ? AND is_core = 1",
            (gid,),
        )
        n_core = cur.fetchone()[0]

        cur = conn.execute(
            "SELECT COUNT(*) FROM pan_genome_features WHERE genome_id = ?",
            (gid,),
        )
        n_genes = cur.fetchone()[0]

        genome_stats[gid] = {
            "n_genes": n_genes,
            "n_clusters": len(clusters),
            "core_pct": round(n_core / len(clusters), 3) if clusters else 0,
        }

    # User genome stats
    cur = conn.execute(
        "SELECT COUNT(*) FROM genome_features WHERE genome_id = ?",
        (USER_GENOME_DISPLAY_ID,),
    )
    user_n_genes = cur.fetchone()[0]

    cur = conn.execute(
        "SELECT pangenome_cluster_id, pangenome_is_core FROM genome_features "
        "WHERE genome_id = ? AND pangenome_cluster_id IS NOT NULL",
        (USER_GENOME_DISPLAY_ID,),
    )
    user_core = 0
    user_with_cluster = 0
    for row in cur:
        user_with_cluster += 1
        if row["pangenome_is_core"] == 1:
            user_core += 1

    genome_stats[USER_GENOME_DISPLAY_ID] = {
        "n_genes": user_n_genes,
        "n_clusters": len(user_clusters),
        "core_pct": round(user_core / user_with_cluster, 3) if user_with_cluster else 0,
    }

    conn.close()

    # --- Step 7: Output JSON ---
    output = {
        "linkage": Z.tolist(),
        "genome_ids": genome_ids,
        "leaf_order": leaf_order,
        "user_genome_id": USER_GENOME_DISPLAY_ID,
        "genome_metadata": metadata,
        "genome_stats": genome_stats,
        "stats": {
            "n_genomes": n_genomes,
            "n_clusters": n_clusters,
            "n_reference": n_genomes - 1,
            "max_distance": float(condensed.max()),
            "min_distance": float(condensed.min()),
        },
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=None, separators=(",", ":"))

    file_size = len(json.dumps(output))
    print(f"\nWrote {OUTPUT_PATH} ({file_size / 1024:.1f} KB)")
    print(f"  {n_genomes} genomes, {len(Z)} linkage rows")
    print(f"  Leaf order: {leaf_order[:3]}... {leaf_order[-1]}")
    print("Done!")


if __name__ == "__main__":
    main()
