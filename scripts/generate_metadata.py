#!/usr/bin/env python3
"""Generate ../data/metadata.json for the Genome Heatmap Viewer.

Extracts genome-specific metadata from the database dynamically.
Supports both old (berdl_tables.db) and new (GenomeDataLakeTables) schemas.
"""

import json
import re
import sqlite3
import sys

DB_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/berdl_tables.db"
OUTPUT_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/../data/metadata.json"


def detect_schema(conn):
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    return 'new' if 'user_feature' in tables else 'old'


def derive_organism_name(genome_id, gtdb_taxonomy, ncbi_taxonomy):
    """Derive a human-readable organism name from available metadata."""
    for taxonomy in [gtdb_taxonomy, ncbi_taxonomy]:
        if taxonomy and taxonomy.strip():
            parts = taxonomy.split(";")
            for part in reversed(parts):
                part = part.strip()
                if part.startswith("s__") and len(part) > 3:
                    return part[3:]

    name = genome_id.replace("user_", "").replace("_RAST", "")
    name = name.replace("_", " ")
    name = re.sub(r'\bK12\b', 'K-12', name)
    return name


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    output_path = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    schema = detect_schema(conn)
    print(f"Detected schema: {schema}")
    print("Extracting genome metadata from database...")

    if schema == 'new':
        # New schema: kind='user', genome column
        user_row = conn.execute(
            "SELECT genome, gtdb_taxonomy, ncbi_taxonomy FROM genome WHERE kind = 'user' LIMIT 1"
        ).fetchone()
        if not user_row:
            print("ERROR: No user genome found (kind='user')")
            sys.exit(1)

        user_genome_id = user_row["genome"]
        gtdb_tax = user_row["gtdb_taxonomy"] or ""
        ncbi_tax = user_row["ncbi_taxonomy"] or ""

        # If user has no taxonomy, try pangenome reference genomes
        if not gtdb_tax and not ncbi_tax:
            ref_row = conn.execute(
                "SELECT gtdb_taxonomy, ncbi_taxonomy FROM genome WHERE kind = 'clade_member' LIMIT 1"
            ).fetchone()
            if ref_row:
                gtdb_tax = ref_row["gtdb_taxonomy"] or ""
                ncbi_tax = ref_row["ncbi_taxonomy"] or ""

        organism_name = derive_organism_name(user_genome_id, gtdb_tax, ncbi_tax)
        taxonomy = gtdb_tax or ncbi_tax or "Unknown"

        n_ref_genomes = conn.execute(
            "SELECT COUNT(DISTINCT genome) FROM pangenome_feature"
        ).fetchone()[0]

        n_genes = conn.execute(
            "SELECT COUNT(*) FROM user_feature WHERE genome = ? AND type = 'gene'",
            (user_genome_id,)
        ).fetchone()[0]

        n_contigs = conn.execute(
            "SELECT COUNT(DISTINCT contig) FROM user_feature WHERE genome = ?",
            (user_genome_id,)
        ).fetchone()[0]

        assembly_id = "Unknown"
        match = re.search(r'(GC[AF]_\d+\.\d+)', user_genome_id)
        if match:
            assembly_id = match.group(1)

    else:
        # Old schema
        user_row = conn.execute(
            "SELECT id, gtdb_taxonomy, ncbi_taxonomy, n_contigs, n_features FROM genome WHERE id LIKE 'user_%' LIMIT 1"
        ).fetchone()
        if not user_row:
            print("ERROR: No user genome found")
            sys.exit(1)

        user_genome_id = user_row["id"]
        organism_name = derive_organism_name(
            user_genome_id,
            user_row["gtdb_taxonomy"],
            user_row["ncbi_taxonomy"]
        )
        taxonomy = user_row["gtdb_taxonomy"] or user_row["ncbi_taxonomy"] or "Unknown"

        n_ref_genomes = conn.execute(
            "SELECT COUNT(*) FROM genome WHERE id NOT LIKE 'user_%'"
        ).fetchone()[0]

        n_genes = conn.execute(
            "SELECT COUNT(*) FROM genome_features WHERE genome_id = ?",
            (user_genome_id,)
        ).fetchone()[0]

        n_contigs = user_row["n_contigs"] or 0

        assembly_id = "Unknown"
        match = re.search(r'(GC[AF]_\d+\.\d+)', user_genome_id)
        if match:
            assembly_id = match.group(1)

    print(f"  User genome: {user_genome_id}")
    print(f"  Organism: {organism_name}")
    print(f"  Reference genomes: {n_ref_genomes}")
    print(f"  Genes: {n_genes}")

    metadata = {
        "organism": organism_name,
        "genome_id": user_genome_id,
        "genome_assembly": assembly_id,
        "n_ref_genomes": n_ref_genomes,
        "n_genes": n_genes,
        "n_contigs": n_contigs,
        "taxonomy": taxonomy,
        "database_type": "GenomeDataLakeTables" if schema == 'new' else "BERDL",
    }

    conn.close()

    with open(output_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nWrote {output_path}")
    print(f"  {organism_name}")
    print(f"  {n_genes} genes, {n_ref_genomes} reference genomes")
    print("Done!")


if __name__ == "__main__":
    main()
