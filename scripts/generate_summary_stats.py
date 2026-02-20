#!/usr/bin/env python3
"""Generate summary statistics for display in the viewer.

Extracts from GenomeDataLakeTables:
1. Gapfilled reactions (from genome_reaction)
2. Growth phenotype summary (from genome_phenotype)
3. Genome comparison stats (from genome + ani)

Usage:
    python3 generate_summary_stats.py DB_PATH [OUTPUT_PATH]
"""

import json
import os
import sqlite3
import sys


def jaccard_similarity(vec_a, vec_b):
    """Compute Jaccard similarity between two binary vectors."""
    intersection = sum(1 for a, b in zip(vec_a, vec_b) if a == 1 and b == 1)
    union = sum(1 for a, b in zip(vec_a, vec_b) if a == 1 or b == 1)
    return intersection / union if union > 0 else 0.0


def build_user_vector(conn, user_genome_id, phenotype_ids):
    """Build P/N vector for user genome matching reference phenotype order."""
    pheno_map = {}
    for row in conn.execute(
        "SELECT phenotype_id, class FROM genome_phenotype WHERE genome_id = ?",
        (user_genome_id,)
    ):
        pheno_map[row["phenotype_id"]] = 1 if row["class"] == "P" else 0
    return [pheno_map.get(pid, 0) for pid in phenotype_ids]


def has_table(conn, table_name):
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return row[0] > 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_summary_stats.py DB_PATH [OUTPUT_PATH]")
        sys.exit(1)

    db_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "summary_stats.json"

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    print("Extracting summary statistics from database...")

    user_genome_row = conn.execute(
        "SELECT genome FROM genome WHERE kind = 'user' LIMIT 1"
    ).fetchone()
    if not user_genome_row:
        print("ERROR: No user genome found")
        sys.exit(1)
    user_genome_id = user_genome_row["genome"]
    print(f"  User genome: {user_genome_id}")

    summary = {}

    # --- Missing functions (derived from gapfilled reactions) ---
    print("Extracting reaction-based missing functions...")
    if has_table(conn, 'genome_reaction'):
        gapfilled = conn.execute("""
            SELECT COUNT(*) FROM genome_reaction
            WHERE genome_id = ? AND gapfilling_status IS NOT NULL AND gapfilling_status != 'none'
        """, (user_genome_id,)).fetchone()[0]

        total_rxns = conn.execute(
            "SELECT COUNT(*) FROM genome_reaction WHERE genome_id = ?",
            (user_genome_id,)
        ).fetchone()[0]

        top_gapfilled = []
        for row in conn.execute("""
            SELECT reaction_id, equation_names, gapfilling_status
            FROM genome_reaction
            WHERE genome_id = ? AND gapfilling_status IS NOT NULL AND gapfilling_status != 'none'
            ORDER BY reaction_id
            LIMIT 20
        """, (user_genome_id,)):
            top_gapfilled.append({
                "reaction": row["reaction_id"],
                "function": row["equation_names"] or "Unknown reaction",
                "pangenome": False,
                "rich_gapfill": "rich" in (row["gapfilling_status"] or "").lower(),
                "min_gapfill": "minimal" in (row["gapfilling_status"] or "").lower(),
            })

        summary["missing_functions"] = {
            "pangenome_missing": 0,
            "gapfilled": gapfilled,
            "total_reactions": total_rxns,
            "top_missing": top_gapfilled,
        }
        print(f"  {total_rxns} total reactions, {gapfilled} gapfilled")
    else:
        summary["missing_functions"] = None
        print("  genome_reaction table not found")

    # --- Growth phenotype summary (from genome_phenotype) ---
    print("Extracting growth phenotype summary...")
    if has_table(conn, 'genome_phenotype'):
        positive = conn.execute("""
            SELECT COUNT(*) FROM genome_phenotype
            WHERE genome_id = ? AND class = 'P'
        """, (user_genome_id,)).fetchone()[0]

        negative = conn.execute("""
            SELECT COUNT(*) FROM genome_phenotype
            WHERE genome_id = ? AND class = 'N'
        """, (user_genome_id,)).fetchone()[0]

        avg_pos_gaps = conn.execute("""
            SELECT AVG(gap_count) FROM genome_phenotype
            WHERE genome_id = ? AND class = 'P'
        """, (user_genome_id,)).fetchone()[0] or 0

        avg_neg_gaps = conn.execute("""
            SELECT AVG(gap_count) FROM genome_phenotype
            WHERE genome_id = ? AND class = 'N'
        """, (user_genome_id,)).fetchone()[0] or 0

        # Gap analysis
        zero_gap = conn.execute("""
            SELECT COUNT(*) FROM genome_phenotype
            WHERE genome_id = ? AND gap_count = 0
        """, (user_genome_id,)).fetchone()[0]

        max_gaps = conn.execute("""
            SELECT MAX(gap_count) FROM genome_phenotype
            WHERE genome_id = ?
        """, (user_genome_id,)).fetchone()[0] or 0

        # Top gapfilled reactions across phenotypes
        top_gapfilled = []
        try:
            for row in conn.execute("""
                SELECT gapfilled_reactions, COUNT(*) as freq
                FROM genome_phenotype
                WHERE genome_id = ? AND gapfilled_reactions IS NOT NULL
                    AND gapfilled_reactions != ''
                GROUP BY gapfilled_reactions
                ORDER BY freq DESC
                LIMIT 10
            """, (user_genome_id,)):
                top_gapfilled.append({
                    "reactions": row[0],
                    "frequency": row[1]
                })
        except sqlite3.OperationalError:
            pass

        summary["growth_phenotypes"] = {
            "positive_growth": positive,
            "negative_growth": negative,
            "avg_positive_gaps": round(avg_pos_gaps, 2),
            "avg_negative_gaps": round(avg_neg_gaps, 2),
            "total_phenotypes": positive + negative,
            "zero_gap_count": zero_gap,
            "max_gap_count": max_gaps,
            "top_gapfilled": top_gapfilled,
        }
        print(f"  {positive} positive growth phenotypes")
        print(f"  {negative} negative growth phenotypes")
        print(f"  {zero_gap} phenotypes with zero gaps, max {max_gaps} gaps")
    else:
        summary["growth_phenotypes"] = None
        print("  genome_phenotype table not found")

    # --- Phenotype Prediction Landscape (per-genome phenotype profiles) ---
    print("Extracting phenotype prediction landscape...")
    if has_table(conn, 'genome_phenotype'):
        phenotype_landscape = {"genomes": [], "user_genome_id": user_genome_id}

        for row in conn.execute("""
            SELECT genome_id,
                   COUNT(CASE WHEN class = 'P' THEN 1 END) as positive,
                   COUNT(CASE WHEN class = 'N' THEN 1 END) as negative,
                   COUNT(*) as total,
                   AVG(gap_count) as avg_gaps,
                   SUM(CASE WHEN gap_count = 0 THEN 1 ELSE 0 END) as no_gap_count,
                   AVG(CASE WHEN observed_objective > 0 THEN 1.0 ELSE NULL END) as accuracy
            FROM genome_phenotype
            GROUP BY genome_id
            ORDER BY genome_id
        """):
            phenotype_landscape["genomes"].append({
                "id": row["genome_id"],
                "positive": row["positive"],
                "negative": row["negative"],
                "total": row["total"],
                "avg_gaps": round(row["avg_gaps"], 2) if row["avg_gaps"] else 0,
                "no_gap_pct": round(row["no_gap_count"] / row["total"], 4) if row["total"] else 0,
                "accuracy": round(row["accuracy"], 4) if row["accuracy"] else None
            })

        # --- Reference phenotype accuracy (Jaccard matching) ---
        ref_path = os.path.join(os.path.dirname(output_path), "reference_phenotypes.json")
        if os.path.exists(ref_path):
            print("  Loading reference phenotypes for Jaccard matching...")
            with open(ref_path) as f:
                ref_data = json.load(f)

            user_vector = build_user_vector(conn, user_genome_id, ref_data["phenotype_ids"])

            best_match = None
            best_similarity = -1
            for ref_genome in ref_data["genomes"]:
                sim = jaccard_similarity(user_vector, ref_genome["vector"])
                if sim > best_similarity:
                    best_similarity = sim
                    best_match = ref_genome

            if best_match:
                for g in phenotype_landscape["genomes"]:
                    if g["id"] == user_genome_id:
                        g["accuracy"] = best_match["accuracy"]
                        g["closest_experimental"] = best_match["id"]
                        g["jaccard_similarity"] = round(best_similarity, 4)
                print(f"  Closest experimental genome: {best_match['id']} "
                      f"(Jaccard={best_similarity:.4f}, accuracy={best_match['accuracy']})")

            phenotype_landscape["reference_accuracies"] = [
                {"id": g["id"], "accuracy": g["accuracy"]}
                for g in ref_data["genomes"]
                if g["accuracy"] is not None
            ]
            phenotype_landscape["has_accuracy"] = True
            print(f"  {len(phenotype_landscape['reference_accuracies'])} reference genomes with accuracy")
        else:
            has_accuracy = any(g["accuracy"] is not None for g in phenotype_landscape["genomes"])
            phenotype_landscape["has_accuracy"] = has_accuracy
            print(f"  No reference_phenotypes.json found, using DB accuracy (available: {has_accuracy})")

        summary["phenotype_landscape"] = phenotype_landscape
        print(f"  {len(phenotype_landscape['genomes'])} genomes with phenotype data")
    else:
        summary["phenotype_landscape"] = None
        print("  genome_phenotype table not found")

    # --- Reference genome stats ---
    print("Extracting reference genome comparison...")
    ref_count = conn.execute(
        "SELECT COUNT(DISTINCT genome) FROM pangenome_feature"
    ).fetchone()[0]

    closest_ani = None
    if has_table(conn, 'ani'):
        row = conn.execute("""
            SELECT MAX(ani) as max_ani FROM ani
            WHERE genome1 = ? OR genome2 = ?
        """, (user_genome_id, user_genome_id)).fetchone()
        if row and row["max_ani"]:
            closest_ani = round(row["max_ani"], 4)

    summary["comparison"] = {
        "n_reference_genomes": ref_count,
        "closest_ani": closest_ani,
    }

    print(f"  {ref_count} reference genomes")
    if closest_ani:
        print(f"  Closest genome ANI: {closest_ani:.2f}%")

    conn.close()

    # Write output
    print(f"\nWriting {output_path}...")
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    size_kb = len(json.dumps(summary, indent=2)) / 1024
    print(f"  File size: {size_kb:.1f} KB")
    print("Done!")


if __name__ == "__main__":
    main()
