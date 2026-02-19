#!/usr/bin/env python3
"""Generate ../data/reactions_data.json for the Datalake Dashboard metabolic map tab.

Usage:
    python3 generate_reactions_data.py DB_PATH [GENES_DATA_PATH] [OUTPUT_PATH]
"""

import json
import re
import sqlite3
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_reactions_data.py DB_PATH [GENES_DATA_PATH] [OUTPUT_PATH]")
        sys.exit(1)

    db_path = sys.argv[1]
    genes_data_path = sys.argv[2] if len(sys.argv) > 2 else "genes_data.json"
    output_path = sys.argv[3] if len(sys.argv) > 3 else "reactions_data.json"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Identify user genome
    user_genome = conn.execute(
        "SELECT genome FROM genome WHERE kind = 'user' LIMIT 1"
    ).fetchone()["genome"]
    print(f"  User genome: {user_genome}")

    # Count total genomes
    n_genomes = conn.execute(
        "SELECT COUNT(DISTINCT genome_id) FROM genome_reaction"
    ).fetchone()[0]
    print(f"  {n_genomes} genomes in comparison")

    # Count genomes per reaction
    print("Counting genomes per reaction...")
    rxn_genomes = {}
    for row in conn.execute("SELECT reaction_id, genome_id FROM genome_reaction"):
        rxn_id = row["reaction_id"]
        if rxn_id not in rxn_genomes:
            rxn_genomes[rxn_id] = set()
        rxn_genomes[rxn_id].add(row["genome_id"])

    # Extract user genome reactions
    print(f"Loading reactions for {user_genome}...")
    reactions = {}
    for row in conn.execute("""
        SELECT reaction_id, genes, equation_names, equation_ids, directionality,
               gapfilling_status, rich_media_flux, rich_media_class,
               minimal_media_flux, minimal_media_class
        FROM genome_reaction
        WHERE genome_id = ?
    """, (user_genome,)):
        rxn_id = row["reaction_id"]
        n_with = len(rxn_genomes.get(rxn_id, set()))
        conservation = round(n_with / n_genomes, 4) if n_genomes > 0 else 0

        flux_rich = row["rich_media_flux"] if row["rich_media_flux"] is not None else 0
        flux_min = row["minimal_media_flux"] if row["minimal_media_flux"] is not None else 0
        class_rich = row["rich_media_class"] or "blocked"
        class_min = row["minimal_media_class"] or "blocked"

        reactions[rxn_id] = {
            "genes": row["genes"] or "",
            "equation": row["equation_names"] or "",
            "equation_ids": row["equation_ids"] or "",
            "directionality": row["directionality"] or "reversible",
            "gapfilling": row["gapfilling_status"] or "none",
            "conservation": conservation,
            "flux_rich": round(flux_rich, 6),
            "flux_min": round(flux_min, 6),
            "class_rich": class_rich,
            "class_min": class_min,
        }

    print(f"  {len(reactions)} reactions loaded")
    conn.close()

    # Build gene index
    print("Building gene index...")
    gene_index = {}
    try:
        with open(genes_data_path) as f:
            genes = json.load(f)

        fid_to_idx = {str(g[1]): i for i, g in enumerate(genes)}

        all_locus_tags = set()
        for rxn in reactions.values():
            gene_str = rxn["genes"]
            if gene_str:
                tags = re.findall(r"[A-Za-z][A-Za-z0-9_]+", gene_str)
                tags = [t for t in tags if t.lower() not in ("or", "and")]
                all_locus_tags.update(tags)

        matched = 0
        for tag in all_locus_tags:
            if tag in fid_to_idx:
                gene_index[tag] = [fid_to_idx[tag]]
                matched += 1
            else:
                matches = [idx for fid, idx in fid_to_idx.items() if tag in fid]
                if matches:
                    gene_index[tag] = matches
                    matched += 1

        print(f"  {matched}/{len(all_locus_tags)} locus tags mapped")
    except Exception as e:
        print(f"  Warning: Could not build gene index: {e}")

    # Stats
    active_rich = sum(1 for r in reactions.values() if r["class_rich"] != "blocked")
    active_min = sum(1 for r in reactions.values() if r["class_min"] != "blocked")
    essential_rich = sum(1 for r in reactions.values() if "essential" in r["class_rich"])
    essential_min = sum(1 for r in reactions.values() if "essential" in r["class_min"])

    stats = {
        "total_reactions": len(reactions),
        "active_rich": active_rich,
        "active_min": active_min,
        "essential_rich": essential_rich,
        "essential_min": essential_min,
        "blocked_rich": len(reactions) - active_rich,
        "blocked_min": len(reactions) - active_min,
    }

    output = {
        "user_genome": user_genome,
        "n_genomes": n_genomes,
        "reactions": reactions,
        "gene_index": gene_index,
        "stats": stats,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    size_kb = len(json.dumps(output, separators=(",", ":"))) / 1024
    print(f"\nWrote {output_path} ({size_kb:.0f} KB)")
    print(f"  Stats: {stats}")
    print("Done!")


if __name__ == "__main__":
    main()
