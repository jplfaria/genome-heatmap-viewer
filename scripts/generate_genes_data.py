#!/usr/bin/env python3
"""Generate ../data/genes_data.json for the Genome Heatmap Viewer.

Extracts gene features from a BERDL SQLite database and produces a compact
JSON array ready for the viewer's multi-track heatmap.

Each gene is a 38-element array. Field indices are defined in config.json.

Supports two DB schemas:
- OLD (berdl_tables.db): genome_features + pan_genome_features tables
- NEW (GenomeDataLakeTables): user_feature + pangenome_feature tables

Usage:
    python3 generate_genes_data.py [DB_PATH]

If DB_PATH is not specified, uses the default path.

Requires: Python 3.8+ (no external dependencies)
"""

import json
import sqlite3
import sys
from collections import defaultdict

# ---------- Configuration ----------

DB_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/berdl_tables.db"
OUTPUT_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/../data/genes_data.json"

# Localization categories (must match config.json categories.localization)
LOC_CATEGORIES = [
    "Cytoplasmic", "CytoMembrane", "Periplasmic",
    "OuterMembrane", "Extracellular", "Unknown",
]
LOC_MAP = {name: i for i, name in enumerate(LOC_CATEGORIES)}
LOC_MAP.update({
    "CytoplasmicMembrane": 1,   # DB uses no-space variant
    "Cytoplasmic Membrane": 1,
    "Outer Membrane": 3,
})

# ---------- Helpers ----------


def detect_schema(conn):
    """Detect DB schema version: 'new' if user_feature table exists, else 'old'."""
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    return 'new' if 'user_feature' in tables else 'old'


def get_ontology_columns(conn, table_name):
    """Discover ontology_* columns in a table via PRAGMA."""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    ont_cols = {}
    for row in cursor.fetchall():
        col_name = row[1]
        if col_name.startswith("ontology_"):
            short = col_name.replace("ontology_", "")
            ont_cols[short] = col_name
    return ont_cols


def safe_get(row, col, default=None):
    """Safely get a column value from a sqlite3.Row."""
    try:
        val = row[col]
        return val if val is not None else default
    except (IndexError, KeyError):
        return default


def parse_cluster_ids(raw):
    """Parse pangenome_cluster value, handling new format with :size suffix."""
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


def count_terms(value):
    """Count semicolon-separated terms in a string."""
    if not value or not value.strip():
        return 0
    return len([t for t in value.split(";") if t.strip()])


def is_hypothetical(func):
    """Check if a function string indicates a generic hypothetical protein."""
    if not func or not func.strip():
        return True
    f = func.strip()
    fl = f.lower()
    if fl == "hypothetical protein":
        return True
    if fl.startswith("fig") and fl.endswith("hypothetical protein"):
        return True
    return False


def parse_json_field(raw):
    """Parse a JSON field into a dict."""
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def compute_specificity(func, gene_names, ko, ec, cog, pfam, go):
    """Compute annotation specificity (0.0-1.0)."""
    if not func or not func.strip():
        return 0.0
    fl = func.lower().strip()
    if fl == "hypothetical protein":
        return 0.0

    signals = []
    if ec and str(ec).strip():
        signals.append(0.9)
    if ko and str(ko).strip():
        signals.append(0.7)
    if gene_names and str(gene_names).strip():
        signals.append(0.6)
    if cog and str(cog).strip():
        signals.append(0.5)
    if go and str(go).strip():
        signals.append(0.5)
    if pfam and str(pfam).strip():
        signals.append(0.4)

    base = max(signals) if signals else 0.3

    if "ec " in fl or "(ec " in fl:
        base = min(1.0, base + 0.1)

    if "conserved protein" in fl and "unknown" in fl:
        base = min(base, 0.2)
    elif any(w in fl for w in ["hypothetical", "uncharacterized", "duf"]):
        base = min(base, 0.3)
    elif any(w in fl for w in ["putative", "predicted", "probable", "possible"]):
        base = min(base, 0.5)

    return round(base, 4)


def compute_consistency(user_annotation, cluster_annotations):
    """Compute consistency score for a single annotation type."""
    if not cluster_annotations:
        return -1
    if not user_annotation or not user_annotation.strip():
        return -1
    matches = sum(1 for ann in cluster_annotations if ann == user_annotation)
    return round(matches / len(cluster_annotations), 4)


# ---------- OLD Schema (berdl_tables.db) ----------


def main_old_schema(conn, db_path):
    """Process genes using old schema (genome_features + pan_genome_features)."""
    import re

    # ── 1. Identify user genome ────────────────────────────────────
    print("Identifying user genome...")
    user_genome_row = conn.execute(
        "SELECT id FROM genome WHERE id LIKE 'user_%' LIMIT 1"
    ).fetchone()
    if not user_genome_row:
        print("ERROR: No user genome found (genome.id LIKE 'user_%')")
        sys.exit(1)
    user_genome_id = user_genome_row["id"]
    print(f"  User genome: {user_genome_id}")

    # ── 2. Load reference genome count ─────────────────────────────
    n_ref = conn.execute(
        "SELECT COUNT(DISTINCT genome_id) FROM pan_genome_features"
    ).fetchone()[0]
    print(f"  {n_ref} reference genomes in pangenome")

    # ── 3. Load pangenome cluster data ─────────────────────────────
    print("Loading pangenome cluster data...")
    cluster_genomes = defaultdict(set)
    for row in conn.execute("SELECT cluster_id, genome_id FROM pan_genome_features"):
        cluster_genomes[row["cluster_id"]].add(row["genome_id"])

    cluster_size = {}
    for row in conn.execute(
        "SELECT cluster_id, COUNT(*) as cnt FROM pan_genome_features GROUP BY cluster_id"
    ):
        cluster_size[row["cluster_id"]] = row["cnt"]

    cluster_is_core = {}
    for row in conn.execute(
        "SELECT DISTINCT cluster_id FROM pan_genome_features WHERE is_core = 1"
    ):
        cluster_is_core[row["cluster_id"]] = True

    print("Loading cluster annotations for consistency computation...")
    cluster_ref_genes = defaultdict(list)
    for row in conn.execute("""
        SELECT cluster_id, genome_id, rast_function, bakta_function,
               ko, cog, pfam, go, ec
        FROM pan_genome_features
        WHERE cluster_id IS NOT NULL
    """):
        cluster_ref_genes[row["cluster_id"]].append(dict(row))
    print(f"  Loaded annotations for {len(cluster_ref_genes)} clusters")

    # ── 4. Load KEGG module data ───────────────────────────────────
    print("Loading KEGG module data...")
    module_kos = {}
    try:
        for row in conn.execute("SELECT id, kos FROM phenotype_module"):
            kos_str = row["kos"] or ""
            kos = set(k.strip() for k in kos_str.split(";") if k.strip())
            if kos:
                module_kos[row["id"]] = kos
        print(f"  {len(module_kos)} modules with KO terms")
    except sqlite3.OperationalError:
        print("  (phenotype_module table not found, n_modules will be 0)")

    # ── 5. Load essentiality data ──────────────────────────────────
    print("Loading phenotype data for essentiality...")
    gene_essentiality = {}
    try:
        for row in conn.execute("""
            SELECT gene_id, AVG(essentiality_fraction) as avg_ess
            FROM gene_phenotypes
            WHERE genome_id = ?
            GROUP BY gene_id
        """, (user_genome_id,)):
            gene_essentiality[row["gene_id"]] = round(row["avg_ess"], 4) if row["avg_ess"] is not None else -1
        print(f"  {len(gene_essentiality)} genes with essentiality data")
    except sqlite3.OperationalError:
        print("  (gene_phenotypes table not found, essentiality will be -1)")

    # ── 6. Load user genome features ───────────────────────────────
    print(f"Loading genome features for {user_genome_id}...")
    feature_rows = conn.execute("""
        SELECT * FROM genome_features
        WHERE genome_id = ?
        ORDER BY start, CAST(feature_id AS INTEGER)
    """, (user_genome_id,)).fetchall()
    print(f"  {len(feature_rows)} features loaded")

    # ── 7. Process each gene ───────────────────────────────────────
    print("Processing genes...")
    genes = []
    flux_class_map = {"essential": 0, "variable": 1, "blocked": 2}

    for order_idx, row in enumerate(feature_rows):
        fid = row["feature_id"]
        length = row["length"]
        start = row["start"]
        strand = 1 if row["strand"] == "+" else 0

        rast_func = row["rast_function"]
        bakta_func = row["bakta_function"]
        func = rast_func if rast_func and rast_func.strip() else bakta_func
        if not func:
            func = "hypothetical protein"

        n_ko = count_terms(row["ko"])
        n_cog = count_terms(row["cog"])
        n_pfam = count_terms(row["pfam"])
        n_go = count_terms(row["go"])
        n_ec = count_terms(row["ec"])

        psortb = row["psortb"] or "Unknown"
        loc = LOC_MAP.get(psortb, LOC_MAP["Unknown"])

        # NEW FIELDS
        reactions = row["reactions"] if "reactions" in row.keys() else ""
        if not reactions:
            reactions = ""
        rich_flux = row["rich_media_flux"] if "rich_media_flux" in row.keys() and row["rich_media_flux"] is not None else -1
        rich_class_str = row["rich_media_class"] if "rich_media_class" in row.keys() else ""
        if not rich_class_str:
            rich_class_str = ""
        rich_class = flux_class_map.get(rich_class_str, -1)
        min_flux = row["minimal_media_flux"] if "minimal_media_flux" in row.keys() and row["minimal_media_flux"] is not None else -1
        min_class_str = row["minimal_media_class"] if "minimal_media_class" in row.keys() else ""
        if not min_class_str:
            min_class_str = ""
        min_class = flux_class_map.get(min_class_str, -1)
        psortb_new = loc
        essentiality = gene_essentiality.get(fid, -1)

        # Pangenome
        cluster_id_raw = row["pangenome_cluster_id"]
        is_core_raw = row["pangenome_is_core"]
        cluster_ids = [c.strip() for c in cluster_id_raw.split(";") if c.strip()] if cluster_id_raw else []

        if cluster_ids:
            best_cons = 0
            best_size = 0
            any_core = False
            for cid in cluster_ids:
                n_with = len(cluster_genomes.get(cid, set()))
                ccons = n_with / n_ref if n_ref > 0 else 0
                if ccons > best_cons:
                    best_cons = ccons
                csize = cluster_size.get(cid, 0)
                if csize > best_size:
                    best_size = csize
                if cid in cluster_is_core:
                    any_core = True
            cons_frac = round(best_cons, 4)
            clust_size = best_size
            if is_core_raw == 1:
                pan_cat = 2
            elif is_core_raw == 0:
                pan_cat = 1
            else:
                pan_cat = 2 if any_core else 1
        else:
            cons_frac = 0
            pan_cat = 0
            clust_size = 0

        # Consistency
        if cluster_ids:
            all_rast_cons, all_ko_cons, all_go_cons, all_ec_cons, all_bakta_cons = [], [], [], [], []
            for cid in cluster_ids:
                ref_genes = cluster_ref_genes.get(cid, [])
                if not ref_genes:
                    continue
                ref_rast = [g["rast_function"] for g in ref_genes if g["rast_function"]]
                if ref_rast:
                    all_rast_cons.append(compute_consistency(rast_func, ref_rast))
                ref_ko = [g["ko"] for g in ref_genes if g["ko"]]
                if ref_ko:
                    all_ko_cons.append(compute_consistency(row["ko"], ref_ko))
                ref_go = [g["go"] for g in ref_genes if g["go"]]
                if ref_go:
                    all_go_cons.append(compute_consistency(row["go"], ref_go))
                ref_ec = [g["ec"] for g in ref_genes if g["ec"]]
                if ref_ec:
                    all_ec_cons.append(compute_consistency(row["ec"], ref_ec))
                ref_bakta = [g["bakta_function"] for g in ref_genes if g["bakta_function"]]
                if ref_bakta:
                    all_bakta_cons.append(compute_consistency(bakta_func, ref_bakta))

            rast_cons = max(all_rast_cons) if all_rast_cons else -1
            ko_cons = max(all_ko_cons) if all_ko_cons else -1
            go_cons = max(all_go_cons) if all_go_cons else -1
            ec_cons = max(all_ec_cons) if all_ec_cons else -1
            bakta_cons = max(all_bakta_cons) if all_bakta_cons else -1
            cons_scores = [s for s in [rast_cons, ko_cons, go_cons, ec_cons, bakta_cons] if s >= 0]
            avg_cons = round(sum(cons_scores) / len(cons_scores), 4) if cons_scores else -1
            ec_avg_cons = ec_cons
            ec_map_cons = -1
        else:
            rast_cons = ko_cons = go_cons = ec_cons = avg_cons = bakta_cons = ec_avg_cons = ec_map_cons = -1

        # Specificity
        if cluster_ids:
            specificity = compute_specificity(
                func, row["gene_names"], row["ko"], row["ec"], row["cog"], row["pfam"], row["go"],
            )
        else:
            specificity = -1

        # Derived
        rast_is_hypo = is_hypothetical(rast_func)
        bakta_is_hypo = is_hypothetical(bakta_func)
        is_hypo_val = 1 if rast_is_hypo and bakta_is_hypo else 0
        gene_names = row["gene_names"]
        has_name = 1 if gene_names and gene_names.strip() else 0

        if rast_is_hypo and bakta_is_hypo:
            agreement = 0
        elif rast_is_hypo or bakta_is_hypo:
            agreement = 1
        elif rast_func and bakta_func and rast_func.strip() == bakta_func.strip():
            agreement = 3
        else:
            agreement = 2

        gene_kos = set()
        ko_str = row["ko"] or ""
        for ko in ko_str.split(";"):
            ko = ko.strip()
            if ko:
                if ko.startswith("KEGG:"):
                    ko = ko[5:]
                gene_kos.add(ko)
        n_modules = 0
        if gene_kos:
            for mod_kos in module_kos.values():
                if gene_kos & mod_kos:
                    n_modules += 1

        prot_len = length

        gene = [
            int(fid.split('.')[-1]) if '.' in fid else order_idx,
            fid, length, start, strand, cons_frac, pan_cat, func,
            n_ko, n_cog, n_pfam, n_go, loc,
            rast_cons, ko_cons, go_cons, ec_cons, avg_cons, bakta_cons, ec_avg_cons,
            specificity, is_hypo_val, has_name, n_ec, agreement,
            clust_size, n_modules, ec_map_cons, prot_len,
            reactions, rich_flux, rich_class, min_flux, min_class, psortb_new, essentiality,
        ]
        genes.append(gene)

    return genes, user_genome_id


# ---------- NEW Schema (GenomeDataLakeTables) ----------


def main_new_schema(conn, db_path):
    """Process genes using new schema (user_feature + pangenome_feature)."""
    import re

    # ── Identify user genome ────────────────────────────────────────
    print("Identifying user genome (new schema)...")
    user_genome_row = conn.execute(
        "SELECT genome FROM genome WHERE kind = 'user' LIMIT 1"
    ).fetchone()
    if not user_genome_row:
        print("ERROR: No user genome found (genome.kind = 'user')")
        sys.exit(1)
    user_genome_id = user_genome_row["genome"]
    print(f"  User genome: {user_genome_id}")

    # ── Discover ontology columns ───────────────────────────────────
    ont_cols = get_ontology_columns(conn, "user_feature")
    pf_ont_cols = get_ontology_columns(conn, "pangenome_feature")
    print(f"  User ontology columns: {list(ont_cols.keys())}")
    print(f"  Pangenome ontology columns: {list(pf_ont_cols.keys())}")

    # ── Reference genome count ──────────────────────────────────────
    n_ref = conn.execute(
        "SELECT COUNT(DISTINCT genome) FROM pangenome_feature"
    ).fetchone()[0]
    print(f"  {n_ref} reference genomes in pangenome")

    # ── Load pangenome cluster data ─────────────────────────────────
    print("Loading pangenome cluster data...")
    cluster_genomes = defaultdict(set)
    for row in conn.execute("SELECT cluster, genome FROM pangenome_feature"):
        cluster_genomes[row["cluster"]].add(row["genome"])

    cluster_size = {}
    for row in conn.execute(
        "SELECT cluster, COUNT(*) as cnt FROM pangenome_feature GROUP BY cluster"
    ):
        cluster_size[row["cluster"]] = row["cnt"]

    cluster_is_core = {}
    for row in conn.execute(
        "SELECT DISTINCT cluster FROM pangenome_feature WHERE is_core = 1"
    ):
        cluster_is_core[row["cluster"]] = True

    # ── Load cluster annotations for consistency ────────────────────
    print("Loading cluster annotations...")
    consistency_sources = {}
    pf_select_cols = ["cluster", "genome"]
    for source, pf_key in [("RAST", "RAST"), ("KEGG", "KEGG"), ("GO", "GO"),
                           ("EC", "EC"), ("bakta_product", "bakta_product")]:
        if pf_key in pf_ont_cols:
            pf_select_cols.append(pf_ont_cols[pf_key])
            consistency_sources[source] = pf_ont_cols[pf_key]

    cluster_ref_genes = defaultdict(list)
    if len(pf_select_cols) > 2:
        query = f"SELECT {', '.join(pf_select_cols)} FROM pangenome_feature WHERE cluster IS NOT NULL"
        for row in conn.execute(query):
            cluster_ref_genes[row["cluster"]].append(dict(row))
    print(f"  Loaded annotations for {len(cluster_ref_genes)} clusters")

    # ── Load essentiality data ──────────────────────────────────────
    print("Loading essentiality data...")
    gene_essentiality = {}
    gene_flux = {}
    flux_class_map = {"essential": 0, "variable": 1, "blocked": 2,
                      "forward_only": 1, "reverse_only": 1}
    try:
        for row in conn.execute("""
            SELECT gene_id,
                   AVG(CASE WHEN rich_media_class = 'essential' THEN 1.0
                            WHEN rich_media_class = 'variable' THEN 0.5
                            ELSE 0.0 END) as avg_ess,
                   MAX(rich_media_flux) as max_rich_flux,
                   MAX(CASE WHEN rich_media_class IS NOT NULL THEN rich_media_class ELSE '' END) as rich_class,
                   MAX(minimal_media_flux) as max_min_flux,
                   MAX(CASE WHEN minimal_media_class IS NOT NULL THEN minimal_media_class ELSE '' END) as min_class
            FROM genome_gene_reaction_essentially_test
            WHERE genome_id = ?
            GROUP BY gene_id
        """, (user_genome_id,)):
            gene_essentiality[row["gene_id"]] = round(row["avg_ess"], 4) if row["avg_ess"] is not None else -1
            gene_flux[row["gene_id"]] = {
                "rich_flux": row["max_rich_flux"] if row["max_rich_flux"] is not None else -1,
                "rich_class": row["rich_class"] or "",
                "min_flux": row["max_min_flux"] if row["max_min_flux"] is not None else -1,
                "min_class": row["min_class"] or "",
            }
        print(f"  {len(gene_essentiality)} genes with essentiality data")
    except sqlite3.OperationalError:
        print("  (essentiality table not found)")

    # ── Load reaction assignments per gene ──────────────────────────
    print("Loading reaction assignments...")
    gene_reactions = defaultdict(set)
    try:
        for row in conn.execute("""
            SELECT genes, reaction_id FROM genome_reaction WHERE genome_id = ?
        """, (user_genome_id,)):
            gene_str = row["genes"] or ""
            rxn_id = row["reaction_id"]
            tags = re.findall(r"[A-Za-z][A-Za-z0-9_]+", gene_str)
            tags = [t for t in tags if t.lower() not in ("or", "and")]
            for tag in tags:
                gene_reactions[tag].add(rxn_id)
        print(f"  {len(gene_reactions)} genes with reaction assignments")
    except sqlite3.OperationalError:
        print("  (genome_reaction table not found)")

    # ── Load user genome features ───────────────────────────────────
    print(f"Loading user features for {user_genome_id}...")
    feature_rows = conn.execute("""
        SELECT * FROM user_feature
        WHERE genome = ? AND type = 'gene'
        ORDER BY start, feature_id
    """, (user_genome_id,)).fetchall()
    print(f"  {len(feature_rows)} gene features loaded")

    # ── Process each gene ───────────────────────────────────────────
    print("Processing genes...")
    genes = []

    for order_idx, row in enumerate(feature_rows):
        fid = row["feature_id"]
        length = row["length"]
        start = row["start"]
        strand = 1 if row["strand"] == "+" else 0

        bakta_func = safe_get(row, ont_cols.get("bakta_product", ""), "")
        rast_func = safe_get(row, ont_cols.get("RAST", ""), "")
        func = rast_func if rast_func and str(rast_func).strip() else bakta_func
        if not func or not str(func).strip():
            func = "hypothetical protein"

        n_ko = count_terms(safe_get(row, ont_cols.get("KEGG", ""), ""))
        n_cog = count_terms(safe_get(row, ont_cols.get("COG", ""), ""))
        n_pfam = count_terms(safe_get(row, ont_cols.get("PFAM", ""), ""))
        n_go = count_terms(safe_get(row, ont_cols.get("GO", ""), ""))
        n_ec = count_terms(safe_get(row, ont_cols.get("EC", ""), ""))

        psortb = safe_get(row, ont_cols.get("primary_localization_psortb", ""), "Unknown") or "Unknown"
        loc = LOC_MAP.get(psortb, LOC_MAP["Unknown"])
        psortb_new_str = safe_get(row, ont_cols.get("secondary_localization_psortb", ""), "Unknown") or "Unknown"
        psortb_new = LOC_MAP.get(psortb_new_str, LOC_MAP["Unknown"])

        # Pangenome
        cluster_ids = parse_cluster_ids(row["pangenome_cluster"])
        is_core_raw = row["pangenome_is_core"]

        if cluster_ids:
            best_cons = 0
            best_size = 0
            any_core = False
            for cid in cluster_ids:
                n_with = len(cluster_genomes.get(cid, set()))
                ccons = n_with / n_ref if n_ref > 0 else 0
                if ccons > best_cons:
                    best_cons = ccons
                csize = cluster_size.get(cid, 0)
                if csize > best_size:
                    best_size = csize
                if cid in cluster_is_core:
                    any_core = True
            cons_frac = round(best_cons, 4)
            clust_size = best_size
            if is_core_raw == 1:
                pan_cat = 2
            elif is_core_raw == 0:
                pan_cat = 1
            else:
                pan_cat = 2 if any_core else 1
        else:
            cons_frac = 0
            pan_cat = 0
            clust_size = 0

        # Consistency
        if cluster_ids:
            all_rast_cons, all_ko_cons, all_go_cons, all_ec_cons, all_bakta_cons = [], [], [], [], []
            for cid in cluster_ids:
                ref_genes = cluster_ref_genes.get(cid, [])
                if not ref_genes:
                    continue
                rast_col = consistency_sources.get("RAST")
                if rast_col and rast_func:
                    ref_vals = [g[rast_col] for g in ref_genes if g.get(rast_col)]
                    if ref_vals:
                        all_rast_cons.append(compute_consistency(rast_func, ref_vals))
                kegg_col = consistency_sources.get("KEGG")
                user_kegg = safe_get(row, ont_cols.get("KEGG", ""), "")
                if kegg_col and user_kegg:
                    ref_vals = [g[kegg_col] for g in ref_genes if g.get(kegg_col)]
                    if ref_vals:
                        all_ko_cons.append(compute_consistency(user_kegg, ref_vals))
                go_col = consistency_sources.get("GO")
                user_go = safe_get(row, ont_cols.get("GO", ""), "")
                if go_col and user_go:
                    ref_vals = [g[go_col] for g in ref_genes if g.get(go_col)]
                    if ref_vals:
                        all_go_cons.append(compute_consistency(user_go, ref_vals))
                ec_col = consistency_sources.get("EC")
                user_ec = safe_get(row, ont_cols.get("EC", ""), "")
                if ec_col and user_ec:
                    ref_vals = [g[ec_col] for g in ref_genes if g.get(ec_col)]
                    if ref_vals:
                        all_ec_cons.append(compute_consistency(user_ec, ref_vals))
                bakta_col = consistency_sources.get("bakta_product")
                if bakta_col and bakta_func:
                    ref_vals = [g[bakta_col] for g in ref_genes if g.get(bakta_col)]
                    if ref_vals:
                        all_bakta_cons.append(compute_consistency(bakta_func, ref_vals))

            rast_cons = max(all_rast_cons) if all_rast_cons else -1
            ko_cons = max(all_ko_cons) if all_ko_cons else -1
            go_cons = max(all_go_cons) if all_go_cons else -1
            ec_cons = max(all_ec_cons) if all_ec_cons else -1
            bakta_cons = max(all_bakta_cons) if all_bakta_cons else -1
            cons_scores = [s for s in [rast_cons, ko_cons, go_cons, ec_cons, bakta_cons] if s >= 0]
            avg_cons = round(sum(cons_scores) / len(cons_scores), 4) if cons_scores else -1
            ec_avg_cons = ec_cons
            ec_map_cons = -1
        else:
            rast_cons = ko_cons = go_cons = ec_cons = avg_cons = bakta_cons = ec_avg_cons = ec_map_cons = -1

        # Specificity
        aliases = safe_get(row, "aliases", "")
        if cluster_ids:
            specificity = compute_specificity(
                func, aliases,
                safe_get(row, ont_cols.get("KEGG", ""), ""),
                safe_get(row, ont_cols.get("EC", ""), ""),
                safe_get(row, ont_cols.get("COG", ""), ""),
                safe_get(row, ont_cols.get("PFAM", ""), ""),
                safe_get(row, ont_cols.get("GO", ""), ""),
            )
        else:
            specificity = -1

        # Derived
        rast_is_hypo = is_hypothetical(rast_func) if rast_func else True
        bakta_is_hypo = is_hypothetical(bakta_func)
        is_hypo_val = 1 if rast_is_hypo and bakta_is_hypo else 0
        has_name = 1 if aliases and str(aliases).strip() else 0

        if rast_func and rast_func.strip():
            if rast_is_hypo and bakta_is_hypo:
                agreement = 0
            elif rast_is_hypo or bakta_is_hypo:
                agreement = 1
            elif rast_func.strip() == (bakta_func or "").strip():
                agreement = 3
            else:
                agreement = 2
        else:
            user_kegg = safe_get(row, ont_cols.get("KEGG", ""), "")
            if not user_kegg and bakta_is_hypo:
                agreement = 0
            elif not user_kegg or bakta_is_hypo:
                agreement = 1
            else:
                agreement = 2

        n_modules = 0

        protein_seq = safe_get(row, "protein_sequence", "")
        if protein_seq and len(protein_seq) > 10:
            prot_len = len(protein_seq)
        else:
            prot_len = length // 3 if length else 0

        reactions = ";".join(sorted(gene_reactions.get(fid, set())))

        flux_data = gene_flux.get(fid, {})
        rich_flux = flux_data.get("rich_flux", -1)
        rich_class = flux_class_map.get(flux_data.get("rich_class", ""), -1)
        min_flux = flux_data.get("min_flux", -1)
        min_class = flux_class_map.get(flux_data.get("min_class", ""), -1)

        essentiality = gene_essentiality.get(fid, -1)

        gene = [
            order_idx, fid, length, start, strand, cons_frac, pan_cat, func,
            n_ko, n_cog, n_pfam, n_go, loc,
            rast_cons, ko_cons, go_cons, ec_cons, avg_cons, bakta_cons, ec_avg_cons,
            specificity, is_hypo_val, has_name, n_ec, agreement,
            clust_size, n_modules, ec_map_cons, prot_len,
            reactions, rich_flux, rich_class, min_flux, min_class, psortb_new, essentiality,
        ]
        genes.append(gene)

    return genes, user_genome_id


# ---------- Main ----------


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    output_path = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_PATH

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    schema = detect_schema(conn)
    print(f"Detected schema: {schema}")

    if schema == 'new':
        genes, user_genome_id = main_new_schema(conn, db_path)
    else:
        genes, user_genome_id = main_old_schema(conn, db_path)

    conn.close()

    # Write output
    with open(output_path, "w") as f:
        json.dump(genes, f, separators=(",", ":"))

    size_kb = len(json.dumps(genes, separators=(",", ":"))) / 1024
    print(f"\nWrote {output_path} ({size_kb:.0f} KB)")
    print(f"  {len(genes)} genes, {len(genes[0]) if genes else 0} fields each")

    # Summary stats
    n_core = sum(1 for g in genes if g[6] == 2)
    n_acc = sum(1 for g in genes if g[6] == 1)
    n_unk = sum(1 for g in genes if g[6] == 0)
    n_hypo = sum(1 for g in genes if g[21] == 1)
    n_named = sum(1 for g in genes if g[22] == 1)
    avg_cons_vals = [g[17] for g in genes if g[17] >= 0]
    avg_avg_cons = sum(avg_cons_vals) / len(avg_cons_vals) if avg_cons_vals else 0
    n_with_flux = sum(1 for g in genes if g[30] >= 0)
    n_with_ess = sum(1 for g in genes if g[35] >= 0)

    print(f"\n  Pangenome: {n_core} core, {n_acc} accessory, {n_unk} unknown")
    print(f"  Hypothetical (both tools): {n_hypo}")
    print(f"  Named genes: {n_named}")
    print(f"  Avg consistency (mean): {avg_avg_cons:.3f}")
    print(f"  Genes with flux data: {n_with_flux} ({100*n_with_flux/len(genes):.1f}%)")
    print(f"  Genes with essentiality data: {n_with_ess} ({100*n_with_ess/len(genes):.1f}%)")
    print("Done!")


if __name__ == "__main__":
    main()
