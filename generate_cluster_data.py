#!/usr/bin/env python3
"""Generate cluster_data.json for the Genome Heatmap Viewer UMAP scatter plot.

Computes two UMAP embeddings of 4617 genes:
1. Gene Features: conservation, consistency scores, annotation counts, etc.
2. Presence/Absence: pangenome cluster membership across reference genomes.
"""

import json
import sqlite3
import sys

import numpy as np
import umap

GENES_DATA_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/genes_data.json"
DB_PATH = "/Users/jplfaria/Downloads/berdl_tables_ontology_terms.db"
OUTPUT_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/cluster_data.json"

# Field indices from genes_data.json (29 fields per gene array)
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
    """Convert value to float, treating -1 (N/A) as 0."""
    if val is None or val == -1:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def main():
    # --- Load gene data ---
    print("Loading genes_data.json...")
    with open(GENES_DATA_PATH) as f:
        genes = json.load(f)
    n_genes = len(genes)
    print(f"  {n_genes} genes loaded")

    # --- Embedding 1: Gene Features ---
    print("Building gene features matrix...")
    feature_fields = [
        ("CONS_FRAC", 1.0),      # conservation fraction
        ("RAST_CONS", 1.0),      # RAST consistency
        ("KO_CONS", 1.0),        # KO consistency
        ("GO_CONS", 1.0),        # GO consistency
        ("EC_CONS", 1.0),        # EC consistency
        ("BAKTA_CONS", 1.0),     # Bakta consistency
        ("AVG_CONS", 1.0),       # average consistency
        ("EC_AVG_CONS", 1.0),    # EC average consistency
        # EC_MAP_CONS removed - always -1 (deprecated field)
        ("SPECIFICITY", 1.0),    # annotation specificity
        ("N_KO", 1.0),           # # KEGG terms
        ("N_COG", 1.0),          # # COG terms
        ("N_PFAM", 1.0),         # # Pfam terms
        ("N_GO", 1.0),           # # GO terms
        ("N_EC", 1.0),           # # EC numbers
        ("N_MODULES", 1.0),      # KEGG module hits
        ("CLUSTER_SIZE", 1.0),   # pangenome cluster size
        ("PROT_LEN", 1.0),       # protein length
        ("IS_HYPO", 1.0),        # hypothetical flag
        ("HAS_NAME", 1.0),       # has gene name
        ("STRAND", 1.0),         # strand
        ("PAN_CAT", 1.0),        # pangenome category (0/1/2)
        ("AGREEMENT", 1.0),      # RAST/Bakta agreement (0-3)
    ]

    feature_matrix = np.zeros((n_genes, len(feature_fields)), dtype=np.float32)
    for i, gene in enumerate(genes):
        for j, (field_name, _) in enumerate(feature_fields):
            feature_matrix[i, j] = safe_float(gene[F[field_name]])

    # Normalize each column to [0, 1]
    for j in range(feature_matrix.shape[1]):
        col = feature_matrix[:, j]
        col_min = col.min()
        col_max = col.max()
        if col_max > col_min:
            feature_matrix[:, j] = (col - col_min) / (col_max - col_min)
        else:
            feature_matrix[:, j] = 0.0

    print(f"  Feature matrix: {feature_matrix.shape}")

    print("Running UMAP on gene features...")
    reducer_features = umap.UMAP(
        n_neighbors=30,
        min_dist=0.1,
        n_components=2,
        metric="euclidean",
        random_state=42,
    )
    embedding_features = reducer_features.fit_transform(feature_matrix)
    print(f"  Features embedding range: x=[{embedding_features[:,0].min():.2f}, {embedding_features[:,0].max():.2f}], "
          f"y=[{embedding_features[:,1].min():.2f}, {embedding_features[:,1].max():.2f}]")

    # --- Embedding 2: Presence/Absence across genomes ---
    print("Building presence/absence matrix from DB...")
    conn = sqlite3.connect(DB_PATH)

    # Get all reference genomes in pangenome
    cur = conn.execute("SELECT DISTINCT genome_id FROM pan_genome_features ORDER BY genome_id")
    ref_genomes = [row[0] for row in cur]
    genome_to_idx = {gid: i for i, gid in enumerate(ref_genomes)}
    n_ref = len(ref_genomes)
    print(f"  {n_ref} reference genomes")

    # Build cluster->genome presence map
    cur = conn.execute("SELECT cluster_id, genome_id FROM pan_genome_features")
    cluster_genomes = {}
    for row in cur:
        cid, gid = row
        if cid not in cluster_genomes:
            cluster_genomes[cid] = set()
        cluster_genomes[cid].add(gid)

    conn.close()

    # For each user gene, get its cluster(s) and build a binary vector of genome presence
    print("Building per-gene presence vectors...")
    presence_matrix = np.zeros((n_genes, n_ref), dtype=np.float32)
    genes_with_clusters = 0

    for i, gene in enumerate(genes):
        # Gene's cluster IDs (could be semicolon-separated in the original data)
        # But in genes_data.json, pan_category encodes: 0=unknown, 1=accessory, 2=core
        # We need the actual cluster IDs. Let's use conservation + category as a proxy,
        # or better: look up cluster from genome_features

        # Actually, we don't have cluster IDs in genes_data.json directly.
        # We'll use the feature-based approach as the primary and construct
        # a simulated presence vector from conservation fraction and category.
        cons = safe_float(gene[F["CONS_FRAC"]])
        cat = int(safe_float(gene[F["PAN_CAT"]]))
        cluster_size = int(safe_float(gene[F["CLUSTER_SIZE"]]))

        if cat > 0 and cons > 0:
            genes_with_clusters += 1
            # Simulate: gene is present in cons * n_ref genomes
            n_present = max(1, int(round(cons * n_ref)))
            # Distribute presence: first n_present genomes (deterministic based on gene index)
            rng = np.random.RandomState(i)
            present_indices = rng.choice(n_ref, size=min(n_present, n_ref), replace=False)
            presence_matrix[i, present_indices] = 1.0

    print(f"  {genes_with_clusters}/{n_genes} genes with cluster assignments")

    # Actually, let's get the REAL cluster-to-genome mapping for a better embedding
    # Re-open DB to get user genome cluster IDs
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT feature_id, pangenome_cluster_id FROM genome_features "
        "WHERE genome_id = '562.61143' AND pangenome_cluster_id IS NOT NULL"
    )
    gene_clusters = {}
    for row in cur:
        fid, cids = row
        gene_clusters[fid] = [c.strip() for c in cids.split(";") if c.strip()]
    conn.close()

    # Map gene FID to index
    fid_to_idx = {}
    for i, gene in enumerate(genes):
        fid_to_idx[gene[F["FID"]]] = i

    # Rebuild presence matrix with real data
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

    # For genes with no cluster (unknown), their row is all zeros.
    # Add a small noise to avoid UMAP issues with identical rows.
    zero_rows = np.where(presence_matrix.sum(axis=1) == 0)[0]
    print(f"  {len(zero_rows)} genes with no pangenome presence (will cluster together)")

    print("Running UMAP on presence/absence...")
    reducer_presence = umap.UMAP(
        n_neighbors=30,
        min_dist=0.1,
        n_components=2,
        metric="jaccard",
        random_state=42,
    )
    # For Jaccard metric, UMAP needs binary data
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

    print(f"\nWriting {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    file_size = len(json.dumps(output))
    print(f"  File size: {file_size / 1024:.1f} KB")
    print(f"  {n_genes} genes, 2 embeddings")
    print("Done!")


if __name__ == "__main__":
    main()
