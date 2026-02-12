#!/usr/bin/env python3
"""Generate reactions_data.json for the Genome Heatmap Viewer metabolic map tab.

Processes genome_reactions.tsv to produce per-reaction data for the user genome
including conservation across reference genomes, flux values, and flux classes.
"""

import csv
import json
import sys

TSV_PATH = "/Users/jplfaria/Downloads/genome_reactions.tsv"
GENES_DATA_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/genes_data.json"
OUTPUT_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/reactions_data.json"


def main():
    # --- Load genome_reactions.tsv ---
    print("Loading genome_reactions.tsv...")
    all_rows = []
    with open(TSV_PATH) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            all_rows.append(row)

    # Identify genomes and user genome
    genomes = set()
    user_genome = None
    for row in all_rows:
        gid = row["genome_id"]
        genomes.add(gid)
        if gid.startswith("user_"):
            user_genome = gid

    if not user_genome:
        print("ERROR: No user genome found (expected genome_id starting with 'user_')")
        sys.exit(1)

    n_genomes = len(genomes)
    print(f"Found {n_genomes} genomes, user genome: {user_genome}")

    # --- Build per-reaction data ---
    # First pass: count genomes per reaction (for conservation)
    rxn_genomes = {}  # reaction_id -> set of genome_ids
    for row in all_rows:
        rxn_id = row["reaction_id"]
        if rxn_id not in rxn_genomes:
            rxn_genomes[rxn_id] = set()
        rxn_genomes[rxn_id].add(row["genome_id"])

    # Second pass: extract user genome reaction data
    reactions = {}
    for row in all_rows:
        if row["genome_id"] != user_genome:
            continue
        rxn_id = row["reaction_id"]
        n_with = len(rxn_genomes[rxn_id])
        conservation = round(n_with / n_genomes, 4)

        reactions[rxn_id] = {
            "genes": row["genes"],
            "equation": row["equation_names"],
            "directionality": row["directionality"],
            "gapfilling": row["gapfilling_status"],
            "conservation": conservation,
            "flux_rich": round(float(row["rich_media_flux"]), 6),
            "flux_min": round(float(row["minimal_media_flux"]), 6),
            "class_rich": row["rich_media_class"],
            "class_min": row["minimal_media_class"],
        }

    print(f"User genome has {len(reactions)} reactions")

    # --- Build gene index ---
    # Try to map gene locus tags to gene indices in genes_data.json
    # This mapping will only work when the reaction data is for the same organism
    gene_index = {}
    try:
        with open(GENES_DATA_PATH) as f:
            genes = json.load(f)
        # Build FID lookup: feature_id -> gene index
        fid_to_idx = {}
        for i, gene in enumerate(genes):
            fid = str(gene[1])  # FID is field index 1
            fid_to_idx[fid] = i

        # Extract all unique locus tags from reaction gene assignments
        import re
        all_locus_tags = set()
        for rxn in reactions.values():
            gene_str = rxn["genes"]
            if gene_str:
                # Extract tokens that look like locus tags (alphanumeric + underscore)
                tags = re.findall(r"[A-Za-z][A-Za-z0-9_]+", gene_str)
                # Filter out boolean operators
                tags = [t for t in tags if t not in ("or", "and")]
                all_locus_tags.update(tags)

        # Try to match locus tags to gene FIDs
        matched = 0
        for tag in all_locus_tags:
            # Try exact match first
            if tag in fid_to_idx:
                gene_index[tag] = [fid_to_idx[tag]]
                matched += 1
            else:
                # Try partial match (locus tag might be part of the FID)
                matches = [
                    idx for fid, idx in fid_to_idx.items() if tag in fid
                ]
                if matches:
                    gene_index[tag] = matches
                    matched += 1

        print(
            f"Gene index: {matched}/{len(all_locus_tags)} locus tags mapped to gene indices"
        )
    except Exception as e:
        print(f"Warning: Could not build gene index: {e}")

    # --- Compute stats ---
    active_rich = sum(
        1 for r in reactions.values() if r["class_rich"] != "blocked"
    )
    active_min = sum(
        1 for r in reactions.values() if r["class_min"] != "blocked"
    )
    essential_rich = sum(
        1 for r in reactions.values() if "essential" in r["class_rich"]
    )
    essential_min = sum(
        1 for r in reactions.values() if "essential" in r["class_min"]
    )

    stats = {
        "total_reactions": len(reactions),
        "active_rich": active_rich,
        "active_min": active_min,
        "essential_rich": essential_rich,
        "essential_min": essential_min,
        "blocked_rich": len(reactions) - active_rich,
        "blocked_min": len(reactions) - active_min,
    }

    # --- Write output ---
    output = {
        "user_genome": user_genome,
        "n_genomes": n_genomes,
        "reactions": reactions,
        "gene_index": gene_index,
        "stats": stats,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    size_kb = len(json.dumps(output, separators=(",", ":"))) / 1024
    print(f"\nWrote {OUTPUT_PATH} ({size_kb:.0f} KB)")
    print(f"Stats: {stats}")


if __name__ == "__main__":
    main()
