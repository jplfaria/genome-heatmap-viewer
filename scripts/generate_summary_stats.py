#!/usr/bin/env python3
"""Generate summary statistics for display in the viewer.

Supports both old (berdl_tables.db) and new (GenomeDataLakeTables) schemas.

Extracts:
1. Missing functions (pangenome core reactions absent from user genome)
2. Growth phenotype summary (model predictions)
3. Genome comparison stats

Output: ../data/summary_stats.json
"""

import json
import sqlite3
import sys

DB_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/berdl_tables.db"
OUTPUT_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/../data/summary_stats.json"


def detect_schema(conn):
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    return 'new' if 'user_feature' in tables else 'old'


def has_table(conn, table_name):
    row = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    ).fetchone()
    return row[0] > 0


def main_old_schema(conn, user_genome_id, output_path):
    summary = {}

    # --- Missing functions ---
    print("Extracting missing functions...")
    if has_table(conn, 'missing_functions'):
        missing_pangenome = conn.execute(
            "SELECT COUNT(*) as count FROM missing_functions WHERE Pangenome = 1"
        ).fetchone()["count"]

        missing_gapfill = conn.execute(
            "SELECT COUNT(*) as count FROM missing_functions WHERE RichGapfill = 1 OR MinimalGapfill = 1"
        ).fetchone()["count"]

        missing_functions = []
        for row in conn.execute("""
            SELECT Reaction, RAST_function, Pangenome, RichGapfill, MinimalGapfill
            FROM missing_functions
            WHERE Pangenome = 1
            ORDER BY RAST_function
            LIMIT 20
        """):
            missing_functions.append({
                "reaction": row["Reaction"],
                "function": row["RAST_function"] or "Unknown function",
                "pangenome": bool(row["Pangenome"]),
                "rich_gapfill": bool(row["RichGapfill"]),
                "min_gapfill": bool(row["MinimalGapfill"]),
            })

        summary["missing_functions"] = {
            "pangenome_missing": missing_pangenome,
            "gapfilled": missing_gapfill,
            "top_missing": missing_functions,
        }
        print(f"  {missing_pangenome} core functions missing from user genome")
        print(f"  {missing_gapfill} functions added by gapfilling")
    else:
        summary["missing_functions"] = None
        print("  missing_functions table not found")

    # --- Growth phenotype summary ---
    print("Extracting growth phenotype summary...")
    if has_table(conn, 'growth_phenotype_summary'):
        growth_row = conn.execute("""
            SELECT positive_growth, negative_growth, avg_positive_growth_gaps, avg_negative_growth_gaps
            FROM growth_phenotype_summary
            WHERE genome_id = ?
        """, (user_genome_id,)).fetchone()

        if growth_row:
            summary["growth_phenotypes"] = {
                "positive_growth": growth_row["positive_growth"],
                "negative_growth": growth_row["negative_growth"],
                "avg_positive_gaps": growth_row["avg_positive_growth_gaps"] or 0,
                "avg_negative_gaps": growth_row["avg_negative_growth_gaps"] or 0,
                "total_phenotypes": growth_row["positive_growth"] + growth_row["negative_growth"],
            }
            print(f"  {growth_row['positive_growth']} positive growth phenotypes")
            print(f"  {growth_row['negative_growth']} negative growth phenotypes")
        else:
            summary["growth_phenotypes"] = None
            print("  No growth phenotype data found")
    else:
        summary["growth_phenotypes"] = None
        print("  growth_phenotype_summary table not found")

    # --- Reference genome stats ---
    print("Extracting reference genome comparison...")
    ref_count = conn.execute(
        "SELECT COUNT(*) as count FROM genome WHERE id NOT LIKE 'user_%'"
    ).fetchone()["count"]

    closest_ani = conn.execute("""
        SELECT MAX(ani) as max_ani FROM genome_ani
        WHERE genome1 = ? OR genome2 = ?
    """, (user_genome_id, user_genome_id)).fetchone()

    summary["comparison"] = {
        "n_reference_genomes": ref_count,
        "closest_ani": round(closest_ani["max_ani"], 4) if closest_ani["max_ani"] else None,
    }

    print(f"  {ref_count} reference genomes")
    if closest_ani["max_ani"]:
        print(f"  Closest genome ANI: {closest_ani['max_ani']:.2f}%")

    return summary


def main_new_schema(conn, user_genome_id, output_path):
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

        # Get top gapfilled reactions
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

    # --- Growth phenotype summary (derived from genome_phenotype) ---
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
        "SELECT COUNT(*) FROM genome WHERE kind != 'user'"
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

    return summary


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    output_path = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    schema = detect_schema(conn)
    print(f"Detected schema: {schema}")
    print("Extracting summary statistics from database...")

    if schema == 'new':
        user_genome_row = conn.execute(
            "SELECT genome FROM genome WHERE kind = 'user' LIMIT 1"
        ).fetchone()
        if not user_genome_row:
            print("ERROR: No user genome found")
            sys.exit(1)
        user_genome_id = user_genome_row["genome"]
        print(f"  User genome: {user_genome_id}")
        summary = main_new_schema(conn, user_genome_id, output_path)
    else:
        user_genome_row = conn.execute(
            "SELECT id FROM genome WHERE id LIKE 'user_%' LIMIT 1"
        ).fetchone()
        if not user_genome_row:
            print("ERROR: No user genome found")
            sys.exit(1)
        user_genome_id = user_genome_row["id"]
        print(f"  User genome: {user_genome_id}")
        summary = main_old_schema(conn, user_genome_id, output_path)

    conn.close()

    # --- Write output ---
    print(f"\nWriting {output_path}...")
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    size_kb = len(json.dumps(summary, indent=2)) / 1024
    print(f"  File size: {size_kb:.1f} KB")
    print("Done!")


if __name__ == "__main__":
    main()
