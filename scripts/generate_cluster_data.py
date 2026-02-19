#!/usr/bin/env python3
"""Generate ../data/cluster_data.json for the Datalake Dashboard UMAP scatter plot.

Computes two UMAP embeddings of genes:
1. Gene Features: conservation, consistency scores, annotation counts, etc.
2. Presence/Absence: pangenome cluster membership across reference genomes.

Usage:
    python3 generate_cluster_data.py DB_PATH GENES_DATA_PATH [OUTPUT_PATH]
"""

import json
import sqlite3
import sys

import numpy as np
import umap

# Field indices from genes_data.json (38 fields per gene array)
F = {
    "ID": 0, "FID": 1, "LENGTH": 2, "START": 3, "STRAND": 4,
    "CONS_FRAC": 5, "PAN_CAT": 6, "FUNC": 7,
    "N_KO": 8, "N_COG": 9, "N_PFAM": 10, "N_GO": 11,
    "LOC": 12, "RAST_CONS": 13, "KO_CONS": 14, "GO_CONS": 15,
    "EC_CONS": 16, "AVG_CONS": 17, "BAKTA_CONS": 18, "EC_AVG_CONS": 19,
    "SPECIFICITY": 20, "IS_HYPO": 21, "HAS_NAME": 22, "N_EC": 23,
    "AGREEMENT": 24, "CLUSTER_SIZE": 25, "N_MODULES": 26,
    "EC_MAP_CONS": 27, "PROT_LEN": 28,
}


def safe_float(val, default=0.0):
    if val is None or val == -1:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def parse_cluster_ids(raw):
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
    if len(sys.argv) < 3:
        print("Usage: python3 generate_cluster_data.py DB_PATH GENES_DATA_PATH [OUTPUT_PATH]")
        sys.exit(1)

    db_path = sys.argv[1]
    genes_data_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else "cluster_data.json"

    # --- Load gene data ---
    print("Loading genes_data.json...")
    with open(genes_data_path) as f:
        genes = json.load(f)
    n_genes = len(genes)
    print(f"  {n_genes} genes loaded")

    # --- Embedding 1: Gene Features ---
    print("Building gene features matrix...")
    feature_fields = [
        ("CONS_FRAC", 1.0), ("RAST_CONS", 1.0), ("KO_CONS", 1.0),
        ("GO_CONS", 1.0), ("EC_CONS", 1.0), ("BAKTA_CONS", 1.0),
        ("AVG_CONS", 1.0), ("EC_AVG_CONS", 1.0), ("SPECIFICITY", 1.0),
        ("N_KO", 1.0), ("N_COG", 1.0), ("N_PFAM", 1.0), ("N_GO", 1.0),
        ("N_EC", 1.0), ("N_MODULES", 1.0), ("CLUSTER_SIZE", 1.0),
        ("PROT_LEN", 1.0), ("IS_HYPO", 1.0), ("HAS_NAME", 1.0),
        ("STRAND", 1.0), ("PAN_CAT", 1.0), ("AGREEMENT", 1.0),
    ]

    feature_matrix = np.zeros((n_genes, len(feature_fields)), dtype=np.float32)
    for i, gene in enumerate(genes):
        for j, (field_name, _) in enumerate(feature_fields):
            feature_matrix[i, j] = safe_float(gene[F[field_name]])

    # Normalize each column to [0, 1]
    for j in range(feature_matrix.shape[1]):
        col = feature_matrix[:, j]
        col_min, col_max = col.min(), col.max()
        if col_max > col_min:
            feature_matrix[:, j] = (col - col_min) / (col_max - col_min)
        else:
            feature_matrix[:, j] = 0.0

    print(f"  Feature matrix: {feature_matrix.shape}")

    print("Running UMAP on gene features...")
    reducer_features = umap.UMAP(
        n_neighbors=30, min_dist=0.1, n_components=2,
        metric="euclidean", random_state=42,
    )
    embedding_features = reducer_features.fit_transform(feature_matrix)
    print(f"  Features embedding range: x=[{embedding_features[:,0].min():.2f}, {embedding_features[:,0].max():.2f}], "
          f"y=[{embedding_features[:,1].min():.2f}, {embedding_features[:,1].max():.2f}]")

    # --- Embedding 2: Presence/Absence across genomes ---
    print("Building presence/absence matrix from DB...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Identify user genome
    user_genome_id = conn.execute(
        "SELECT genome FROM genome WHERE kind = 'user' LIMIT 1"
    ).fetchone()["genome"]

    # Get all reference genomes
    ref_genomes = [row["genome"] for row in conn.execute(
        "SELECT DISTINCT genome FROM pangenome_feature ORDER BY genome"
    )]
    genome_to_idx = {gid: i for i, gid in enumerate(ref_genomes)}
    n_ref = len(ref_genomes)
    print(f"  {n_ref} reference genomes")

    # Build cluster->genome presence map
    cluster_genomes = {}
    for row in conn.execute("SELECT cluster, genome FROM pangenome_feature"):
        cid = row["cluster"]
        if cid not in cluster_genomes:
            cluster_genomes[cid] = set()
        cluster_genomes[cid].add(row["genome"])

    # Get user gene cluster assignments
    gene_clusters = {}
    for row in conn.execute("""
        SELECT feature_id, pangenome_cluster FROM user_feature
        WHERE genome = ? AND pangenome_cluster IS NOT NULL AND type = 'gene'
    """, (user_genome_id,)):
        fid = row["feature_id"]
        gene_clusters[fid] = parse_cluster_ids(row["pangenome_cluster"])
    conn.close()

    # Map gene FID to index
    fid_to_idx = {gene[F["FID"]]: i for i, gene in enumerate(genes)}

    # Build presence matrix with real cluster data
    presence_matrix = np.zeros((n_genes, n_ref), dtype=np.float32)
    mapped = 0
    for fid, clusters in gene_clusters.items():
        if fid not in fid_to_idx:
            continue
        gi = fid_to_idx[fid]
        for cid in clusters:
            if cid in cluster_genomes:
                for gid in cluster_genomes[cid]:
                    if gid in genome_to_idx:
                        presence_matrix[gi, genome_to_idx[gid]] = 1.0
                mapped += 1

    print(f"  Mapped {mapped} gene-cluster assignments to presence vectors")

    zero_rows = np.where(presence_matrix.sum(axis=1) == 0)[0]
    print(f"  {len(zero_rows)} genes with no pangenome presence")

    print("Running UMAP on presence/absence...")
    reducer_presence = umap.UMAP(
        n_neighbors=30, min_dist=0.1, n_components=2,
        metric="jaccard", random_state=42,
    )
    embedding_presence = reducer_presence.fit_transform(presence_matrix)
    print(f"  Presence embedding range: x=[{embedding_presence[:,0].min():.2f}, {embedding_presence[:,0].max():.2f}], "
          f"y=[{embedding_presence[:,1].min():.2f}, {embedding_presence[:,1].max():.2f}]")

    # --- Output ---
    output = {
        "features": {
            "x": np.round(embedding_features[:, 0], 4).tolist(),
            "y": np.round(embedding_features[:, 1], 4).tolist(),
        },
        "presence": {
            "x": np.round(embedding_presence[:, 0], 4).tolist(),
            "y": np.round(embedding_presence[:, 1], 4).tolist(),
        },
    }

    print(f"\nWriting {output_path}...")
    with open(output_path, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    file_size = len(json.dumps(output)) / 1024
    print(f"  File size: {file_size:.1f} KB")
    print(f"  {n_genes} genes, 2 embeddings")
    print("Done!")


if __name__ == "__main__":
    main()
