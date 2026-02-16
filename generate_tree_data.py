#!/usr/bin/env python3
"""Generate tree_data.json for the Genome Heatmap Viewer dendrogram.

NEW IN v2.0: Handles split tables (genome_features + pan_genome_features).
User genome ID is now dynamic (detected as 'user_*').

Computes Jaccard distances on pangenome cluster presence/absence,
runs UPGMA hierarchical clustering, and collects genome metadata.
"""

import json
import sqlite3
import sys

import numpy as np
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.spatial.distance import pdist, squareform

DB_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/berdl_tables.db"
OUTPUT_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/tree_data.json"


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # --- Step 1: Identify user genome ---
    print("Identifying user genome...")
    user_genome_row = conn.execute(
        "SELECT id FROM genome WHERE id LIKE 'user_%' LIMIT 1"
    ).fetchone()
    if not user_genome_row:
        print("ERROR: No user genome found")
        sys.exit(1)
    user_genome_id = user_genome_row["id"]
    print(f"  User genome: {user_genome_id}")

    # --- Step 2: Build cluster sets per genome ---
    print("Loading reference genome clusters from pan_genome_features...")
    cur = conn.execute("SELECT genome_id, cluster_id FROM pan_genome_features WHERE cluster_id IS NOT NULL")
    ref_clusters = {}
    for row in cur:
        gid = row["genome_id"]
        cid = row["cluster_id"]
        if gid not in ref_clusters:
            ref_clusters[gid] = set()
        ref_clusters[gid].add(cid)

    print(f"  {len(ref_clusters)} reference genomes loaded")

    print("Loading user genome clusters from genome_features...")
    cur = conn.execute("""
        SELECT pangenome_cluster_id FROM genome_features
        WHERE genome_id = ? AND pangenome_cluster_id IS NOT NULL
    """, (user_genome_id,))
    user_clusters = set()
    for row in cur:
        cluster_str = row["pangenome_cluster_id"]
        if cluster_str:
            for cid in cluster_str.split(";"):
                cid = cid.strip()
                if cid:
                    user_clusters.add(cid)
    print(f"  User genome has {len(user_clusters)} clusters")

    # Combine: user genome first, then references sorted
    all_clusters_by_genome = {user_genome_id: user_clusters}
    for gid in sorted(ref_clusters.keys()):
        all_clusters_by_genome[gid] = ref_clusters[gid]

    genome_ids = list(all_clusters_by_genome.keys())
    n_genomes = len(genome_ids)
    print(f"Total genomes: {n_genomes}")

    # --- Step 3: Build binary presence/absence matrix ---
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

    # --- Step 4: Compute pairwise Jaccard distances ---
    print("Computing Jaccard distance matrix...")
    condensed = pdist(matrix, metric="jaccard")
    dist_matrix = squareform(condensed)
    print(f"  Distance range: {condensed.min():.4f} - {condensed.max():.4f}")

    # --- Step 5: UPGMA hierarchical clustering ---
    print("Running UPGMA clustering...")
    Z = linkage(condensed, method="average")
    leaf_order_indices = leaves_list(Z)
    leaf_order = [genome_ids[i] for i in leaf_order_indices]

    # --- Step 6: Genome metadata ---
    print("Loading genome metadata...")
    metadata = {}

    # From genome table
    cur = conn.execute(
        "SELECT id, gtdb_taxonomy, ncbi_taxonomy, n_contigs, n_features FROM genome"
    )
    genome_table = {}
    for row in cur:
        genome_table[row["id"]] = dict(row)

    # Get ANI data (if available)
    ani_data = {}
    try:
        cur = conn.execute(
            "SELECT genome1, genome2, ani FROM genome_ani WHERE genome1 = ? OR genome2 = ?",
            (user_genome_id, user_genome_id)
        )
        for row in cur:
            other = row["genome2"] if row["genome1"] == user_genome_id else row["genome1"]
            ani_data[other] = round(row["ani"], 4) if row["ani"] else None
    except sqlite3.OperationalError:
        print("  (genome_ani table not found, ANI values will be unavailable)")

    # Build metadata dict
    for gid in genome_ids:
        gdata = genome_table.get(gid, {})
        metadata[gid] = {
            "taxonomy": gdata.get("gtdb_taxonomy") or gdata.get("ncbi_taxonomy") or "Unknown",
            "n_features": gdata.get("n_features", 0),
            "n_contigs": gdata.get("n_contigs", 0),
            "ani_to_user": ani_data.get(gid) if gid != user_genome_id else 1.0,
        }

    # --- Step 7: Per-genome stats ---
    print("Computing per-genome stats...")
    genome_stats = {}
    for gid in genome_ids:
        clusters = all_clusters_by_genome[gid]
        n_clusters = len(clusters)

        # Count actual genes for this genome
        if gid == user_genome_id:
            # User genome: count from genome_features
            n_genes = conn.execute("""
                SELECT COUNT(*) FROM genome_features
                WHERE genome_id = ?
            """, (gid,)).fetchone()[0]

            core_count = conn.execute("""
                SELECT COUNT(*) FROM genome_features
                WHERE genome_id = ? AND pangenome_is_core = 1
            """, (gid,)).fetchone()[0]
        else:
            # Reference genome: count from pan_genome_features
            n_genes = conn.execute("""
                SELECT COUNT(*) FROM pan_genome_features
                WHERE genome_id = ?
            """, (gid,)).fetchone()[0]

            core_count = conn.execute("""
                SELECT COUNT(*) FROM pan_genome_features
                WHERE genome_id = ? AND is_core = 1
            """, (gid,)).fetchone()[0]

        core_pct = round(core_count / n_genes, 4) if n_genes > 0 else 0

        genome_stats[gid] = {
            "n_genes": n_genes,
            "n_clusters": n_clusters,
            "core_pct": core_pct,
        }

    conn.close()

    # --- Step 8: Overall stats ---
    stats = {
        "n_genomes": n_genomes,
        "n_clusters": n_clusters,
        "n_reference": n_genomes - 1,
        "max_distance": round(float(condensed.max()), 4),
        "min_distance": round(float(condensed.min()), 4),
    }

    # --- Step 9: Write output ---
    output = {
        "linkage": Z.tolist(),  # (n-1) x 4 linkage matrix
        "genome_ids": genome_ids,
        "leaf_order": leaf_order,
        "user_genome_id": user_genome_id,
        "genome_metadata": metadata,
        "genome_stats": genome_stats,
        "stats": stats,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    size_kb = len(json.dumps(output, separators=(",", ":"))) / 1024
    print(f"\nWrote {OUTPUT_PATH} ({size_kb:.0f} KB)")
    print(f"  {n_genomes} genomes, {n_clusters} clusters")
    print(f"  Distance range: {stats['min_distance']:.4f} - {stats['max_distance']:.4f}")
    print("Done!")


if __name__ == "__main__":
    main()
