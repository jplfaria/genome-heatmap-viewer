#!/usr/bin/env python3
"""Generate genes_data.json for the Genome Heatmap Viewer.

Extracts gene features from a BERDL SQLite database and produces a compact
JSON array ready for the viewer's multi-track heatmap.

Each gene is a 36-element array. Field indices are defined in config.json.

NEW IN v2.0 (Phase 0 - New DB Schema):
- Supports split tables: genome_features (user genome) + pan_genome_features (references)
- Computes consistency scores from cluster annotations (not pre-computed)
- Adds 7 new fields: REACTIONS, RICH_FLUX, RICH_CLASS, MIN_FLUX, MIN_CLASS, PSORTB_NEW, ESSENTIALITY

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
OUTPUT_PATH = "/Users/jplfaria/repos/genome-heatmap-viewer/genes_data.json"

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


def count_terms(value):
    """Count semicolon-separated terms in a string."""
    if not value or not value.strip():
        return 0
    return len([t for t in value.split(";") if t.strip()])


def is_hypothetical(func):
    """Check if a function string indicates a generic hypothetical protein.

    Returns True only for generic hypothetical annotations like:
      - "hypothetical protein"
      - "FIG00640418: hypothetical protein"
    Returns False for NAMED hypothetical proteins like:
      - "Hypothetical protein YhiL"
      - "Hypothetical response regulatory protein ygeK"
    """
    if not func or not func.strip():
        return True
    f = func.strip()
    fl = f.lower()
    # Exact match (case-insensitive)
    if fl == "hypothetical protein":
        return True
    # FIG prefix patterns: "FIG00640418: hypothetical protein"
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


def compute_specificity(rast_func, bakta_func, gene_names, ko, ec, cog, pfam, go):
    """Compute annotation specificity (0.0-1.0) based on annotation precision.

    Measures how detailed/specific the functional annotation is, as distinct
    from consistency (which measures cluster agreement).

      1.0 = highly specific (EC number + named enzyme)
      0.0 = no functional information (hypothetical protein, no ontology)
     -1.0 = not applicable (no pangenome cluster)

    Scoring: take the best evidence signal, then apply text-based modifiers.

      Evidence signals (take max):
        EC number assigned     → 0.9
        KO term assigned       → 0.7
        Gene name assigned     → 0.6
        COG or GO assigned     → 0.5
        Pfam domain assigned   → 0.4
        Function text only     → 0.3

      Bonuses:
        EC cited in function text → +0.1

      Caps (vague annotation text limits the score):
        "putative"/"predicted"                      → cap 0.5
        "uncharacterized"/"DUF"/"hypothetical ..."  → cap 0.3
        "conserved protein of unknown function"     → cap 0.2
        "hypothetical protein" (generic)            → 0.0
    """
    # Use best available function text (RAST preferred, Bakta fallback)
    func = rast_func if rast_func and rast_func.strip() else bakta_func
    if not func or not func.strip():
        return 0.0
    fl = func.lower().strip()

    # Generic hypothetical = zero specificity
    if fl == "hypothetical protein":
        return 0.0

    # Evidence signals from ontology assignments
    signals = []
    if ec and ec.strip():
        signals.append(0.9)
    if ko and ko.strip():
        signals.append(0.7)
    if gene_names and gene_names.strip():
        signals.append(0.6)
    if cog and cog.strip():
        signals.append(0.5)
    if go and go.strip():
        signals.append(0.5)
    if pfam and pfam.strip():
        signals.append(0.4)

    # Base score: best evidence, or 0.3 if only function text
    base = max(signals) if signals else 0.3

    # Bonus: EC number cited in function text (extra precision)
    if "ec " in fl or "(ec " in fl:
        base = min(1.0, base + 0.1)

    # Caps for vague annotation language
    if "conserved protein" in fl and "unknown" in fl:
        base = min(base, 0.2)
    elif any(w in fl for w in ["hypothetical", "uncharacterized", "duf"]):
        base = min(base, 0.3)
    elif any(w in fl for w in ["putative", "predicted", "probable", "possible"]):
        base = min(base, 0.5)

    return round(base, 4)


def compute_consistency(user_annotation, cluster_annotations):
    """Compute consistency score for a single annotation type.

    Compares the user genome's annotation against all reference genome genes
    in the same pangenome cluster.

    Args:
        user_annotation: User genome's annotation value (string)
        cluster_annotations: List of annotation values from cluster members

    Returns:
        float: 0.0-1.0 (fraction of cluster members matching user), or -1 if N/A
    """
    if not cluster_annotations:
        return -1  # No cluster members
    if not user_annotation or not user_annotation.strip():
        return -1  # User has no annotation

    # Count matches
    matches = sum(1 for ann in cluster_annotations if ann == user_annotation)
    return round(matches / len(cluster_annotations), 4)


# ---------- Main ----------


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

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

    # cluster_id -> set of genome_ids (for conservation)
    cluster_genomes = defaultdict(set)
    for row in conn.execute("SELECT cluster_id, genome_id FROM pan_genome_features"):
        cluster_genomes[row["cluster_id"]].add(row["genome_id"])

    # cluster_id -> gene count (for cluster_size)
    cluster_size = {}
    for row in conn.execute(
        "SELECT cluster_id, COUNT(*) as cnt FROM pan_genome_features GROUP BY cluster_id"
    ):
        cluster_size[row["cluster_id"]] = row["cnt"]

    # cluster_id -> is_core flag (for multi-cluster gene classification)
    cluster_is_core = {}
    for row in conn.execute(
        "SELECT DISTINCT cluster_id, is_core FROM pan_genome_features WHERE is_core = 1"
    ):
        cluster_is_core[row["cluster_id"]] = True

    # cluster_id -> {genome_id -> gene_row} (for consistency computation)
    # Load ALL annotations from reference genomes for each cluster
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

    # ── 4. Load KEGG module data (for n_modules) ───────────────────

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

    # ── 5. Load phenotype data for essentiality (OPTIONAL) ─────────

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

    for order_idx, row in enumerate(feature_rows):
        fid = row["feature_id"]
        length = row["length"]
        start = row["start"]
        strand = 1 if row["strand"] == "+" else 0

        rast_func = row["rast_function"]
        bakta_func = row["bakta_function"]

        # FUNC: prefer RAST, fall back to Bakta
        func = rast_func if rast_func and rast_func.strip() else bakta_func
        if not func:
            func = "hypothetical protein"

        # Ontology term counts
        n_ko = count_terms(row["ko"])
        n_cog = count_terms(row["cog"])
        n_pfam = count_terms(row["pfam"])
        n_go = count_terms(row["go"])
        n_ec = count_terms(row["ec"])

        # Localization (PSORTb)
        psortb = row["psortb"] or "Unknown"
        loc = LOC_MAP.get(psortb, LOC_MAP["Unknown"])

        # ── NEW FIELDS (indices 29-35) ─────────────────────────────

        # REACTIONS [29]: semicolon-separated reaction IDs
        reactions = row["reactions"] if "reactions" in row.keys() else ""
        if not reactions:
            reactions = ""

        # RICH_FLUX [30]: rich media flux
        rich_flux = row["rich_media_flux"] if "rich_media_flux" in row.keys() and row["rich_media_flux"] is not None else -1

        # RICH_CLASS [31]: rich media flux class (essential/variable/blocked)
        rich_class_str = row["rich_media_class"] if "rich_media_class" in row.keys() else ""
        if not rich_class_str:
            rich_class_str = ""
        # Map to index: essential=0, variable=1, blocked=2
        rich_class_map = {"essential": 0, "variable": 1, "blocked": 2}
        rich_class = rich_class_map.get(rich_class_str, -1)

        # MIN_FLUX [32]: minimal media flux
        min_flux = row["minimal_media_flux"] if "minimal_media_flux" in row.keys() and row["minimal_media_flux"] is not None else -1

        # MIN_CLASS [33]: minimal media flux class
        min_class_str = row["minimal_media_class"] if "minimal_media_class" in row.keys() else ""
        if not min_class_str:
            min_class_str = ""
        min_class = rich_class_map.get(min_class_str, -1)

        # PSORTB_NEW [34]: Updated PSORTb (may be sparser than old DB)
        # For now, same as LOC field; keep for compatibility
        psortb_new = loc

        # ESSENTIALITY [35]: Average essentiality_fraction from gene_phenotypes
        essentiality = gene_essentiality.get(fid, -1)

        # ── Pangenome cluster data ─────────────────────────────────

        cluster_id_raw = row["pangenome_cluster_id"]
        is_core_raw = row["pangenome_is_core"]

        if cluster_id_raw:
            cluster_ids = [c.strip() for c in cluster_id_raw.split(";") if c.strip()]
        else:
            cluster_ids = []

        if cluster_ids:
            # Conservation: fraction of ref genomes with this cluster
            # For multi-cluster genes, take the max (per Chris's guidance)
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
                # Check is_core for this cluster in pan_genome_features
                if cid in cluster_is_core and cluster_is_core[cid]:
                    any_core = True
            cons_frac = round(best_cons, 4)
            clust_size = best_size

            # Pan category: Core (2), Accessory (1), Unknown (0)
            if is_core_raw == 1:
                pan_cat = 2
            elif is_core_raw == 0:
                pan_cat = 1
            else:
                # Multi-cluster genes have NULL is_core in genome_features;
                # check if ANY of their clusters is marked core
                pan_cat = 2 if any_core else 1
        else:
            cons_frac = 0
            pan_cat = 0
            clust_size = 0

        # ── Consistency scores (COMPUTE from cluster annotations) ──

        if cluster_ids:
            # For multi-cluster genes, compute consistency for EACH cluster and take MAX
            # (consistent with conservation computation which also uses MAX)
            # This ensures 266 multi-cluster genes get the best consistency score
            all_rast_cons = []
            all_ko_cons = []
            all_go_cons = []
            all_ec_cons = []
            all_bakta_cons = []

            for cid in cluster_ids:
                ref_genes = cluster_ref_genes.get(cid, [])
                if not ref_genes:
                    continue

                # RAST consistency for this cluster
                ref_rast = [g["rast_function"] for g in ref_genes if g["rast_function"]]
                if ref_rast:
                    all_rast_cons.append(compute_consistency(rast_func, ref_rast))

                # KO consistency for this cluster
                ref_ko = [g["ko"] for g in ref_genes if g["ko"]]
                if ref_ko:
                    all_ko_cons.append(compute_consistency(row["ko"], ref_ko))

                # GO consistency for this cluster
                ref_go = [g["go"] for g in ref_genes if g["go"]]
                if ref_go:
                    all_go_cons.append(compute_consistency(row["go"], ref_go))

                # EC consistency for this cluster
                ref_ec = [g["ec"] for g in ref_genes if g["ec"]]
                if ref_ec:
                    all_ec_cons.append(compute_consistency(row["ec"], ref_ec))

                # Bakta consistency for this cluster
                ref_bakta = [g["bakta_function"] for g in ref_genes if g["bakta_function"]]
                if ref_bakta:
                    all_bakta_cons.append(compute_consistency(bakta_func, ref_bakta))

            # Take MAX consistency across all clusters (or -1 if no valid scores)
            rast_cons = max(all_rast_cons) if all_rast_cons else -1
            ko_cons = max(all_ko_cons) if all_ko_cons else -1
            go_cons = max(all_go_cons) if all_go_cons else -1
            ec_cons = max(all_ec_cons) if all_ec_cons else -1
            bakta_cons = max(all_bakta_cons) if all_bakta_cons else -1

            # Average consistency (exclude -1 values)
            cons_scores = [s for s in [rast_cons, ko_cons, go_cons, ec_cons, bakta_cons] if s >= 0]
            avg_cons = round(sum(cons_scores) / len(cons_scores), 4) if cons_scores else -1

            # EC average consistency (for now, same as ec_cons)
            ec_avg_cons = ec_cons

            # EC mapped consistency (not available in new DB, set to -1)
            ec_map_cons = -1

        else:
            # No cluster - all consistency scores are N/A
            rast_cons = ko_cons = go_cons = ec_cons = avg_cons = bakta_cons = ec_avg_cons = ec_map_cons = -1

        # ── Annotation specificity ─────────────────────────────────

        if cluster_ids:
            specificity = compute_specificity(
                rast_func, bakta_func, row["gene_names"],
                row["ko"], row["ec"], row["cog"], row["pfam"], row["go"],
            )
        else:
            specificity = -1  # no cluster

        # ── Derived boolean/categorical fields ─────────────────────

        # IS_HYPO: 1 if BOTH RAST and Bakta say hypothetical
        rast_is_hypo = is_hypothetical(rast_func)
        bakta_is_hypo = is_hypothetical(bakta_func)
        is_hypo_val = 1 if rast_is_hypo and bakta_is_hypo else 0

        # HAS_NAME: 1 if gene has an official gene name
        gene_names = row["gene_names"]
        has_name = 1 if gene_names and gene_names.strip() else 0

        # AGREEMENT: RAST/Bakta annotation agreement
        # 0 = Both Hypothetical, 1 = One Hypothetical, 2 = Disagree, 3 = Agree
        if rast_is_hypo and bakta_is_hypo:
            agreement = 0
        elif rast_is_hypo or bakta_is_hypo:
            agreement = 1
        elif (
            rast_func
            and bakta_func
            and rast_func.strip() == bakta_func.strip()
        ):
            agreement = 3
        else:
            agreement = 2

        # N_MODULES: count KEGG modules hit by this gene's KO terms
        gene_kos = set()
        ko_str = row["ko"] or ""
        for ko in ko_str.split(";"):
            ko = ko.strip()
            if ko:
                # DB stores "KEGG:K11904", modules use bare "K11904"
                if ko.startswith("KEGG:"):
                    ko = ko[5:]
                gene_kos.add(ko)
        n_modules = 0
        if gene_kos:
            for mod_kos in module_kos.values():
                if gene_kos & mod_kos:
                    n_modules += 1

        # Protein length (in this DB, length IS protein length in aa)
        prot_len = length

        # ── Build gene array (36 fields) ───────────────────────────

        gene = [
            int(fid.split('.')[-1]) if '.' in fid else order_idx,  # [0]  ID (extract int from feature_id)
            fid,            # [1]  FID (feature_id string)
            length,         # [2]  LENGTH (protein length, aa)
            start,          # [3]  START (genome position)
            strand,         # [4]  STRAND (1=forward, 0=reverse)
            cons_frac,      # [5]  CONS_FRAC (fraction of ref genomes)
            pan_cat,        # [6]  PAN_CAT (0=Unknown, 1=Accessory, 2=Core)
            func,           # [7]  FUNC (RAST or Bakta function)
            n_ko,           # [8]  N_KO
            n_cog,          # [9]  N_COG
            n_pfam,         # [10] N_PFAM
            n_go,           # [11] N_GO
            loc,            # [12] LOC (PSORTb category index)
            rast_cons,      # [13] RAST_CONS
            ko_cons,        # [14] KO_CONS
            go_cons,        # [15] GO_CONS
            ec_cons,        # [16] EC_CONS
            avg_cons,       # [17] AVG_CONS
            bakta_cons,     # [18] BAKTA_CONS
            ec_avg_cons,    # [19] EC_AVG_CONS
            specificity,    # [20] SPECIFICITY
            is_hypo_val,    # [21] IS_HYPO
            has_name,       # [22] HAS_NAME
            n_ec,           # [23] N_EC
            agreement,      # [24] AGREEMENT
            clust_size,     # [25] CLUSTER_SIZE
            n_modules,      # [26] N_MODULES
            ec_map_cons,    # [27] EC_MAP_CONS
            prot_len,       # [28] PROT_LEN
            # ── NEW FIELDS ─────────────────────────────────────────
            reactions,      # [29] REACTIONS (semicolon-separated)
            rich_flux,      # [30] RICH_FLUX
            rich_class,     # [31] RICH_CLASS (0=essential, 1=variable, 2=blocked, -1=N/A)
            min_flux,       # [32] MIN_FLUX
            min_class,      # [33] MIN_CLASS
            psortb_new,     # [34] PSORTB_NEW (same as LOC for now)
            essentiality,   # [35] ESSENTIALITY
        ]
        genes.append(gene)

    conn.close()

    # ── 8. Write output ────────────────────────────────────────────

    with open(OUTPUT_PATH, "w") as f:
        json.dump(genes, f, separators=(",", ":"))

    size_kb = len(json.dumps(genes, separators=(",", ":"))) / 1024
    print(f"\nWrote {OUTPUT_PATH} ({size_kb:.0f} KB)")
    print(f"  {len(genes)} genes, 36 fields each")

    # ── 9. Summary statistics ──────────────────────────────────────

    n_core = sum(1 for g in genes if g[6] == 2)
    n_acc = sum(1 for g in genes if g[6] == 1)
    n_unk = sum(1 for g in genes if g[6] == 0)
    n_hypo = sum(1 for g in genes if g[21] == 1)
    n_named = sum(1 for g in genes if g[22] == 1)
    avg_cons_vals = [g[17] for g in genes if g[17] >= 0]
    avg_avg_cons = sum(avg_cons_vals) / len(avg_cons_vals) if avg_cons_vals else 0

    # Count genes with flux data
    n_with_flux = sum(1 for g in genes if g[30] >= 0)  # RICH_FLUX >= 0
    n_with_ess = sum(1 for g in genes if g[35] >= 0)   # ESSENTIALITY >= 0

    print(f"\n  Pangenome: {n_core} core, {n_acc} accessory, {n_unk} unknown")
    print(f"  Hypothetical (both tools): {n_hypo}")
    print(f"  Named genes: {n_named}")
    print(f"  Avg consistency (mean): {avg_avg_cons:.3f}")
    print(f"  Genes with flux data: {n_with_flux} ({100*n_with_flux/len(genes):.1f}%)")
    print(f"  Genes with essentiality data: {n_with_ess} ({100*n_with_ess/len(genes):.1f}%)")

    # Agreement breakdown
    agree_counts = [0, 0, 0, 0]
    for g in genes:
        agree_counts[g[24]] += 1
    labels = ["Both Hypo", "One Hypo", "Disagree", "Agree"]
    print(f"  RAST/Bakta agreement: " + ", ".join(
        f"{labels[i]}={agree_counts[i]}" for i in range(4)
    ))

    print("Done!")


if __name__ == "__main__":
    main()
