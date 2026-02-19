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
import sqlite3
import sys


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

        summary["growth_phenotypes"] = {
            "positive_growth": positive,
            "negative_growth": negative,
            "avg_positive_gaps": round(avg_pos_gaps, 2),
            "avg_negative_gaps": round(avg_neg_gaps, 2),
            "total_phenotypes": positive + negative,
        }
        print(f"  {positive} positive growth phenotypes")
        print(f"  {negative} negative growth phenotypes")
    else:
        summary["growth_phenotypes"] = None
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
