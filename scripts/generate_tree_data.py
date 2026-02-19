#!/usr/bin/env python3
"""Generate ../data/tree_data.json for the Genome Heatmap Viewer dendrogram.

Supports both old (berdl_tables.db) and new (GenomeDataLakeTables) schemas.

Computes Jaccard distances on pangenome cluster presence/absence,
runs UPGMA hierarchical clustering, and collects genome metadata.
"""

import json
import sqlite3
import sys
from collections import defaultdict

import numpy as np
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.spatial.distance import pdist, squareform

DB_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/berdl_tables.db"
OUTPUT_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/../data/tree_data.json"


def detect_schema(conn):
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    return 'new' if 'user_feature' in tables else 'old'


def parse_cluster_ids(raw):
    """Parse cluster IDs, handling new format with :size suffix."""
    if not raw or not str(raw).strip():
        return []
    parts = []
    for part in str(raw).split(";"):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            part = part.rsplit(":", 1)[0].strip()
        parts.append(part)
    return parts


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    output_path = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    schema = detect_schema(conn)
    print(f"Detected schema: {schema}")

    if schema == 'new':
        # New schema: genome table has 'genome' column and 'kind' field
        user_genome_row = conn.execute(
            "SELECT genome FROM genome WHERE kind = 'user' LIMIT 1"
        ).fetchone()
        if not user_genome_row:
            print("ERROR: No user genome found")
            sys.exit(1)
        user_genome_id = user_genome_row["genome"]
        print(f"  User genome: {user_genome_id}")

        # Reference genomes from pangenome_feature
        print("Loading reference genome clusters from pangenome_feature...")
        ref_clusters = defaultdict(set)
        for row in conn.execute("SELECT genome, cluster FROM pangenome_feature WHERE cluster IS NOT NULL"):
            ref_clusters[row["genome"]].add(row["cluster"])
        print(f"  {len(ref_clusters)} reference genomes loaded")

        # User genome clusters from user_feature
        print("Loading user genome clusters from user_feature...")
        user_clusters = set()
        for row in conn.execute("""
            SELECT pangenome_cluster FROM user_feature
            WHERE genome = ? AND pangenome_cluster IS NOT NULL
        """, (user_genome_id,)):
            for cid in parse_cluster_ids(row["pangenome_cluster"]):
                user_clusters.add(cid)
        print(f"  User genome has {len(user_clusters)} clusters")

        # Genome metadata columns
        genome_id_col = "genome"
        genome_table_query = "SELECT * FROM genome"

        # ANI table
        ani_table = "ani"

        # Gene count queries
        def user_gene_count(gid):
            return conn.execute(
                "SELECT COUNT(*) FROM user_feature WHERE genome = ? AND type = 'gene'",
                (gid,)
            ).fetchone()[0]

        def user_core_count(gid):
            return conn.execute(
                "SELECT COUNT(*) FROM user_feature WHERE genome = ? AND pangenome_is_core = 1",
                (gid,)
            ).fetchone()[0]

        def ref_gene_count(gid):
            return conn.execute(
                "SELECT COUNT(*) FROM pangenome_feature WHERE genome = ?",
                (gid,)
            ).fetchone()[0]

        def ref_core_count(gid):
            return conn.execute(
                "SELECT COUNT(*) FROM pangenome_feature WHERE genome = ? AND is_core = 1",
                (gid,)
            ).fetchone()[0]

    else:
        # Old schema
        user_genome_row = conn.execute(
            "SELECT id FROM genome WHERE id LIKE 'user_%' LIMIT 1"
        ).fetchone()
        if not user_genome_row:
            print("ERROR: No user genome found")
            sys.exit(1)
        user_genome_id = user_genome_row["id"]
        print(f"  User genome: {user_genome_id}")

        print("Loading reference genome clusters from pan_genome_features...")
        ref_clusters = defaultdict(set)
        for row in conn.execute("SELECT genome_id, cluster_id FROM pan_genome_features WHERE cluster_id IS NOT NULL"):
            ref_clusters[row["genome_id"]].add(row["cluster_id"])
        print(f"  {len(ref_clusters)} reference genomes loaded")

        print("Loading user genome clusters from genome_features...")
        user_clusters = set()
        for row in conn.execute("""
            SELECT pangenome_cluster_id FROM genome_features
            WHERE genome_id = ? AND pangenome_cluster_id IS NOT NULL
        """, (user_genome_id,)):
            for cid in row["pangenome_cluster_id"].split(";"):
                cid = cid.strip()
                if cid:
                    user_clusters.add(cid)
        print(f"  User genome has {len(user_clusters)} clusters")

        genome_id_col = "id"
        genome_table_query = "SELECT * FROM genome"
        ani_table = "genome_ani"

        def user_gene_count(gid):
            return conn.execute(
                "SELECT COUNT(*) FROM genome_features WHERE genome_id = ?", (gid,)
            ).fetchone()[0]

        def user_core_count(gid):
            return conn.execute(
                "SELECT COUNT(*) FROM genome_features WHERE genome_id = ? AND pangenome_is_core = 1", (gid,)
            ).fetchone()[0]

        def ref_gene_count(gid):
            return conn.execute(
                "SELECT COUNT(*) FROM pan_genome_features WHERE genome_id = ?", (gid,)
            ).fetchone()[0]

        def ref_core_count(gid):
            return conn.execute(
                "SELECT COUNT(*) FROM pan_genome_features WHERE genome_id = ? AND is_core = 1", (gid,)
            ).fetchone()[0]

    # ── Common logic ────────────────────────────────────────────────────

    all_clusters_by_genome = {user_genome_id: user_clusters}
    for gid in sorted(ref_clusters.keys()):
        all_clusters_by_genome[gid] = ref_clusters[gid]

    genome_ids = list(all_clusters_by_genome.keys())
    n_genomes = len(genome_ids)
    print(f"Total genomes: {n_genomes}")

    # Build binary matrix
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
            if cid in cluster_to_idx:
                matrix[gi, cluster_to_idx[cid]] = 1

    # Jaccard distances + UPGMA
    print("Computing Jaccard distance matrix...")
    condensed = pdist(matrix, metric="jaccard")
    print(f"  Distance range: {condensed.min():.4f} - {condensed.max():.4f}")

    print("Running UPGMA clustering...")
    Z = linkage(condensed, method="average")
    leaf_order = [genome_ids[i] for i in leaves_list(Z)]

    # Genome metadata
    print("Loading genome metadata...")
    genome_table = {}
    for row in conn.execute(genome_table_query):
        gid = row[genome_id_col]
        genome_table[gid] = dict(row)

    # ANI data
    ani_data = {}
    try:
        for row in conn.execute(
            f"SELECT genome1, genome2, ani FROM {ani_table} WHERE genome1 = ? OR genome2 = ?",
            (user_genome_id, user_genome_id)
        ):
            other = row["genome2"] if row["genome1"] == user_genome_id else row["genome1"]
            ani_data[other] = round(row["ani"], 4) if row["ani"] else None
    except sqlite3.OperationalError:
        print(f"  ({ani_table} table not found, ANI values will be unavailable)")

    metadata = {}
    for gid in genome_ids:
        gdata = genome_table.get(gid, {})
        metadata[gid] = {
            "taxonomy": gdata.get("gtdb_taxonomy") or gdata.get("ncbi_taxonomy") or "Unknown",
            "n_features": gdata.get("n_features") or gdata.get("size", 0),
            "n_contigs": gdata.get("n_contigs", 0),
            "ani_to_user": ani_data.get(gid) if gid != user_genome_id else 1.0,
        }

    # Per-genome stats
    print("Computing per-genome stats...")
    genome_stats = {}
    for gid in genome_ids:
        clusters = all_clusters_by_genome[gid]
        if gid == user_genome_id:
            n_genes = user_gene_count(gid)
            core_count = user_core_count(gid)
        else:
            n_genes = ref_gene_count(gid)
            core_count = ref_core_count(gid)

        genome_stats[gid] = {
            "n_genes": n_genes,
            "n_clusters": len(clusters),
            "core_pct": round(core_count / n_genes, 4) if n_genes > 0 else 0,
        }

    conn.close()

    # Output
    stats = {
        "n_genomes": n_genomes,
        "n_clusters": n_clusters,
        "n_reference": n_genomes - 1,
        "max_distance": round(float(condensed.max()), 4),
        "min_distance": round(float(condensed.min()), 4),
    }

    output = {
        "linkage": Z.tolist(),
        "genome_ids": genome_ids,
        "leaf_order": leaf_order,
        "user_genome_id": user_genome_id,
        "genome_metadata": metadata,
        "genome_stats": genome_stats,
        "stats": stats,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    size_kb = len(json.dumps(output, separators=(",", ":"))) / 1024
    print(f"\nWrote {output_path} ({size_kb:.0f} KB)")
    print(f"  {n_genomes} genomes, {n_clusters} clusters")
    print("Done!")


if __name__ == "__main__":
    main()
