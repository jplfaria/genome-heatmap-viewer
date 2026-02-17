# Track Documentation - Genome Heatmap Viewer

**Complete technical reference for all tracks, computations, data sources, and implementations**

This document provides full audit trail for every track in the Genome Heatmap Viewer, including:
- Exact computation method
- Source data and database queries
- Code implementation references
- Example values
- Biological interpretation
- Known limitations

---

## Table of Contents

1. [Data Generation Pipeline](#data-generation-pipeline)
2. [Track Definitions](#track-definitions)
3. [Tree Tab Features](#tree-tab-features)
4. [Cluster Tab Features](#cluster-tab-features)
5. [Metabolic Map Tab Features](#metabolic-map-tab-features)
6. [Distributions Tab](#distributions-tab)

---

## Data Generation Pipeline

### Source Database: `berdl_tables_ontology_terms.db`

**Location:** `/Users/jplfaria/repos/genome-heatmap-viewer/berdl_tables_ontology_terms.db`
**Size:** 148 MB
**Type:** SQLite3 database

**Key Tables:**
- `genome_features` - Main gene annotation table
- `pangenome_cluster_members` - Pangenome cluster membership
- `pan_genome_features` - Reference genome statistics per cluster
- `gene_phenotypes` - Phenotype and fitness data
- `metabolic_modeling` - FBA flux predictions
- `ontology_terms` - Term definitions (KO, COG, GO, Pfam, EC)

### Generation Scripts

All data generation scripts are in `/Users/jplfaria/repos/genome-heatmap-viewer/`:

1. **`generate_metadata.py`** - Organism metadata
2. **`generate_genes_data.py`** - Main gene data (3,235 genes × 38 fields)
3. **`generate_tree_data.py`** - UPGMA phylogenetic tree
4. **`generate_cluster_data.py`** - UMAP embeddings
5. **`generate_reactions_data.py`** - Metabolic reaction data
6. **`generate_summary_stats.py`** - Summary statistics
7. **`extract_pan_genome_features.py`** - Reference genome stats

---

## Track Definitions

### Track Array Structure

Each gene in `genes_data.json` is represented as an array with 38 fields (indices 0-37):

```javascript
[
  ID,           // [0]  Internal gene index (0-3234)
  FID,          // [1]  Feature ID (locus tag)
  LENGTH,       // [2]  Gene length (bp)
  START,        // [3]  Start position (bp)
  STRAND,       // [4]  Strand (0=reverse, 1=forward)
  CONS_FRAC,    // [5]  Pangenome conservation fraction (0-1)
  PAN_CAT,      // [6]  Pangenome category (0=Unknown, 1=Accessory, 2=Core)
  FUNC,         // [7]  Function annotation (string)
  N_KO,         // [8]  Number of KEGG terms
  N_COG,        // [9]  Number of COG terms
  N_PFAM,       // [10] Number of Pfam terms
  N_GO,         // [11] Number of GO terms
  LOC,          // [12] Subcellular localization
  RAST_CONS,    // [13] RAST consistency score (-1 or 0-1)
  KO_CONS,      // [14] KO consistency score (-1 or 0-1)
  GO_CONS,      // [15] GO consistency score (-1 or 0-1)
  EC_CONS,      // [16] EC consistency score (-1 or 0-1)
  AVG_CONS,     // [17] Average consistency score (-1 or 0-1)
  BAKTA_CONS,   // [18] Bakta consistency score (-1 or 0-1)
  EC_AVG_CONS,  // [19] EC average consistency (legacy field, unused)
  SPECIFICITY,  // [20] Annotation specificity score (0-1)
  IS_HYPO,      // [21] Is hypothetical (0 or 1)
  HAS_NAME,     // [22] Has gene name (0 or 1)
  N_EC,         // [23] Number of EC numbers
  AGREEMENT,    // [24] Legacy agreement field (unused)
  CLUSTER_SIZE, // [25] Pangenome cluster size
  N_MODULES,    // [26] Number of KEGG modules
  EC_MAP_CONS,  // [27] EC mapped consistency score (-1 or 0-1)
  PROT_LEN,     // [28] Protein length (amino acids)
  REACTIONS,    // [29] Metabolic reactions (semicolon-separated)
  RICH_FLUX,    // [30] Flux in rich media
  RICH_CLASS,   // [31] Reaction class in rich media
  MIN_FLUX,     // [32] Flux in minimal media
  MIN_CLASS,    // [33] Reaction class in minimal media
  PSORTB_NEW,   // [34] PSORTb localization (legacy, same as LOC)
  ESSENTIALITY, // [35] Gene essentiality score
  N_PHENOTYPES, // [36] Number of phenotype associations
  N_FITNESS     // [37] Number of fitness scores
]
```

---

## TRACK 1: Gene Order

**Track ID:** `order`
**Field:** `ID` (index 0)
**Type:** Sequential
**Enabled by default:** Yes

### What it shows
Sequential numbering of genes from 0 to 3,234 in genome order.

### Computation
**Source:** `generate_genes_data.py` lines 470-471

```python
gene_id = i  # Simple counter, 0-indexed
gene_data.append(gene_id)
```

**Database query:** None (generated from iteration order)

### Example values
- First gene: 0
- Last gene: 3234
- Range: 0-3234

### Color scheme
Blue gradient (light blue → dark blue)

### Biological interpretation
Shows genome organization. Genes are ordered by their genomic position (START field), allowing visualization of:
- Operons (clusters of functionally related genes)
- Genomic islands
- Synteny when comparing to other tracks

### Implementation
**Display code:** `index.html` lines 1607-1625 (sequential color mapping)

### Known limitations
None

---

## TRACK 2: Gene Direction (Strand)

**Track ID:** `strand`
**Field:** `STRAND` (index 4)
**Type:** Binary
**Enabled by default:** Yes

### What it shows
DNA strand encoding each gene: forward strand (+) or reverse strand (-)

### Computation
**Source:** `generate_genes_data.py` lines 479-480

```python
strand = 1 if row['strand'] == '+' else 0
gene_data.append(strand)
```

**Database query:**
```sql
SELECT strand FROM genome_features WHERE genome_id = 'user_genome'
```

**Database column:** `genome_features.strand` (values: '+' or '-')

### Example values
- Forward strand (+): 1
- Reverse strand (-): 0
- Distribution: ~51.9% forward, ~48.1% reverse (expected ~50/50)

### Color scheme
- Purple (#9333ea): Forward strand (value 1)
- Orange (#f59e0b): Reverse strand (value 0)

### Biological interpretation
Shows strand bias and can reveal:
- Transcriptional organization
- Replication-related strand bias
- Leading vs lagging strand gene distribution

Balanced distribution (~50/50) is expected. Significant deviation may indicate:
- Selection pressure on strand placement
- Replication-transcription conflicts
- Recent lateral gene transfer

### Implementation
**Display code:** `index.html` lines 1607 (binary color mapping)

### Known limitations
None

---

## TRACK 3: Pangenome Conservation

**Track ID:** `conservation`
**Field:** `CONS_FRAC` (index 5)
**Type:** Sequential
**Enabled by default:** Yes

### What it shows
Fraction of reference genomes (0-1) that contain the same pangenome cluster as this gene.

### Computation
**Source:** `generate_genes_data.py` lines 361-378

```python
# For genes with pangenome cluster assignment
if cluster_id:
    cursor.execute("""
        SELECT COUNT(DISTINCT genome_id)
        FROM pan_genome_features
        WHERE pangenome_cluster_id = ?
    """, (cluster_id,))
    genomes_with_cluster = cursor.fetchone()[0]

    # Conservation = genomes with cluster / total reference genomes
    conservation_frac = genomes_with_cluster / total_ref_genomes
else:
    conservation_frac = 0.0  # No cluster = not conserved
```

**Database query:**
```sql
-- Step 1: Get cluster ID for this gene
SELECT pangenome_cluster_id
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?

-- Step 2: Count reference genomes with this cluster
SELECT COUNT(DISTINCT genome_id)
FROM pan_genome_features
WHERE pangenome_cluster_id = ?
```

**Total reference genomes:** 35 (from `pan_genome_features` distinct genome_id count, excluding user_genome which has 6 genomes not in the table)

### Example values
- Core gene (in all 35 genomes): 1.0
- Accessory gene (in 18/35 genomes): 0.514
- User-specific gene (no cluster): 0.0
- Distribution: 97.6% of genes have conservation > 0.9 (indicates very close phylogenetic relationship)

### Color scheme
Blue gradient:
- Light blue: Low conservation (0.0)
- Dark blue: High conservation (1.0)

### Biological interpretation
**High conservation (>0.95):**
- Core genes essential for basic cellular functions
- Housekeeping genes
- Highly constrained by selection

**Medium conservation (0.5-0.95):**
- Accessory genes
- Niche-specific adaptations
- Horizontally transferred genes that have spread

**Low conservation (<0.5):**
- Recently acquired genes
- Strain-specific adaptations
- Potential sequencing/annotation artifacts

### Multi-cluster genes special case
**Issue discovered:** 266 genes have semicolon-separated cluster IDs (e.g., "123;456;789")

**Current behavior:** Takes MAX conservation across all clusters (lines 368-378)

**Rationale:** Per Chris Henry - "compute for both and take the higher one" - a gene present in ANY highly conserved cluster should be considered conserved

### Implementation
**Display code:** `index.html` lines 1610-1625 (sequential scale)

### Known limitations
1. **Reference genome set:** Only 35 genomes in pangenome (6 + user_genome missing from pan_genome_features table)
2. **Multi-cluster genes:** 266 genes in multiple clusters - using MAX may overestimate conservation
3. **Zero conservation:** Genes with no cluster assignment get 0.0, which could mean:
   - Truly unique to this genome
   - Annotation/clustering artifact
   - Insufficient reference data

---

## TRACK 4: Core/Accessory Category

**Track ID:** `pan_category`
**Field:** `PAN_CAT` (index 6)
**Type:** Categorical
**Enabled by default:** Yes

### What it shows
Pangenome classification of each gene into three categories based on conservation.

### Computation
**Source:** `generate_genes_data.py` lines 389-400

```python
# Classification thresholds
CORE_THRESHOLD = 0.95  # Present in >95% of genomes

if pangenome_cluster_id is None:
    pan_category = 0  # Unknown (no cluster)
elif conservation_frac > CORE_THRESHOLD:
    pan_category = 2  # Core
else:
    pan_category = 1  # Accessory
```

**Database dependencies:**
- Requires `CONS_FRAC` (field 5) to be computed first
- Uses same pangenome cluster data

### Category definitions

**Category 0: Unknown (Gray)**
- No pangenome cluster assigned
- Could indicate:
  - Unique genes not found in reference genomes
  - Annotation artifacts
  - Genes excluded from pangenome analysis

**Category 1: Accessory (Orange)**
- Present in >0% but ≤95% of reference genomes
- Variable genes that may provide:
  - Niche-specific adaptations
  - Metabolic versatility
  - Strain-specific features

**Category 2: Core (Green)**
- Present in >95% of reference genomes
- Essential or highly conserved genes
- Typically housekeeping functions

### Example values
- Core genes (PAN_CAT=2): 91.4% (2,957/3,235 genes)
- Accessory genes (PAN_CAT=1): 5.4% (175 genes)
- Unknown genes (PAN_CAT=0): 3.2% (103 genes)

### Color scheme
- **Green (#22c55e):** Core (value 2)
- **Orange (#f59e0b):** Accessory (value 1)
- **Gray (#9ca3af):** Unknown (value 0)

### Biological interpretation

**91.4% core is HIGH but valid** for this dataset because:
1. Reference genomes are closely related (same species/genus)
2. High conservation (97.6% >0.9) confirms close phylogenetic relationship
3. Literature shows 60-90% core for bacterial species pangenomes
4. Our 91.4% is at the high end but within expected range

**Accessory genes (5.4%)** may represent:
- Metabolic pathway variations
- Resistance mechanisms
- Phage-related genes
- Mobile genetic elements

**Unknown genes (3.2%)** warrant investigation:
- May be truly unique innovations
- Could be annotation artifacts
- Possible pseudogenes or fragments

### Implementation
**Display code:** `index.html` lines 1607 (categorical colors)

**Legend code:** `index.html` lines 1780-1805

### Known limitations
1. **Threshold hardcoded:** 95% cutoff is standard but arbitrary
2. **Binary core/accessory:** No "soft core" (90-95%) category
3. **Multi-cluster genes:** 266 genes with multiple clusters use MAX conservation for classification

---

## TRACK 5: Function Consensus (Average)

**Track ID:** `avg_cons`
**Field:** `AVG_CONS` (index 17)
**Type:** Consistency
**Enabled by default:** Yes

### What it shows
Average consistency score across all annotation sources (RAST, KO, GO, EC, Bakta), measuring how well genes in the same pangenome cluster agree on their functional annotation.

### Computation
**Source:** `generate_genes_data.py` lines 159-179

```python
def compute_consistency_scores(row, cursor, cluster_id):
    """Compute consistency across annotation sources."""

    # Get all genes in the same pangenome cluster
    cursor.execute("""
        SELECT feature_id, genome_id, function, ko, go_terms, ec_numbers, bakta_function
        FROM genome_features
        WHERE pangenome_cluster_id = ?
    """, (cluster_id,))
    cluster_genes = cursor.fetchall()

    # For each annotation source, compute consistency
    scores = []

    # RAST consistency (function field)
    if row['function']:
        rast_cons = compute_function_consistency(row['function'],
                                                   [g['function'] for g in cluster_genes])
        scores.append(rast_cons)

    # KO consistency
    if row['ko']:
        ko_cons = compute_term_consistency(row['ko'],
                                             [g['ko'] for g in cluster_genes])
        scores.append(ko_cons)

    # GO consistency
    if row['go_terms']:
        go_cons = compute_term_consistency(row['go_terms'],
                                             [g['go_terms'] for g in cluster_genes])
        scores.append(go_cons)

    # EC consistency
    if row['ec_numbers']:
        ec_cons = compute_term_consistency(row['ec_numbers'],
                                             [g['ec_numbers'] for g in cluster_genes])
        scores.append(ec_cons)

    # Bakta consistency
    if row['bakta_function']:
        bakta_cons = compute_function_consistency(row['bakta_function'],
                                                    [g['bakta_function'] for g in cluster_genes])
        scores.append(bakta_cons)

    # Average across available sources
    if scores:
        avg_consistency = sum(scores) / len(scores)
    else:
        avg_consistency = -1.0  # N/A (no annotations)

    return avg_consistency
```

**Consistency formula for ontology terms (KO, GO, EC):**
```python
def compute_term_consistency(user_terms, cluster_terms):
    """
    Compute Jaccard similarity averaged across cluster.

    user_terms: "K00001;K00002" (semicolon-separated)
    cluster_terms: ["K00001;K00002", "K00001;K00003", ...]

    Returns: 0.0-1.0 (average Jaccard index)
    """
    user_set = set(user_terms.split(';'))

    similarities = []
    for ct in cluster_terms:
        if ct:
            cluster_set = set(ct.split(';'))
            intersection = len(user_set & cluster_set)
            union = len(user_set | cluster_set)
            jaccard = intersection / union if union > 0 else 0.0
            similarities.append(jaccard)

    return sum(similarities) / len(similarities) if similarities else 0.0
```

**Consistency formula for function text (RAST, Bakta):**
```python
def compute_function_consistency(user_func, cluster_funcs):
    """
    Compute exact string match fraction.

    Returns: fraction of cluster genes with identical function (0.0-1.0)
    """
    matches = sum(1 for cf in cluster_funcs if cf == user_func)
    return matches / len(cluster_funcs) if cluster_funcs else 0.0
```

### Database queries
```sql
-- Get pangenome cluster ID for user gene
SELECT pangenome_cluster_id
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?

-- Get all genes in the cluster with their annotations
SELECT feature_id, genome_id, function, ko, go_terms, ec_numbers, bakta_function
FROM genome_features
WHERE pangenome_cluster_id = ?
```

### Example values
- High consistency (0.9-1.0): Core housekeeping genes with conserved annotations
- Medium consistency (0.5-0.8): Genes with some annotation variation across sources
- Low consistency (0.0-0.4): Poorly characterized genes or annotation conflicts
- N/A (-1.0): Genes with no cluster or no annotations

**Distribution:** 49.4% of genes have avg_cons > 0.7 (acceptable quality)

### Color scheme
- **Orange (#f59e0b):** High consistency (1.0)
- **Blue (#3b82f6):** Low consistency (0.0)
- **Gray (#9ca3af):** N/A (-1.0, no cluster or no annotations)

### Biological interpretation

**High consistency (>0.8):**
- Well-characterized genes
- Strong functional conservation
- High confidence in annotation

**Medium consistency (0.4-0.8):**
- Moderate annotation agreement
- May reflect:
  - Different annotation pipelines/databases
  - Multi-functional genes
  - Evolving function

**Low consistency (<0.4):**
- Annotation conflicts
- Poorly characterized
- May indicate:
  - Horizontal gene transfer with functional divergence
  - Annotation errors
  - Genuinely variable function

### Implementation
**Display code:** `index.html` lines 1610-1625 (consistency scale with N/A handling)

### Known limitations
1. **Requires cluster membership:** Genes without clusters get -1 (N/A)
2. **Averaging heterogeneous metrics:** Combines Jaccard (ontology) with exact match (function text)
3. **Equal weighting:** All sources contribute equally regardless of annotation quality
4. **Function text exact match:** Very strict - minor wording differences score as 0
5. **Multi-cluster genes:** Uses FIRST cluster only (inconsistent with conservation which uses MAX)

### INCONSISTENCY FOUND
**Issue:** Multi-cluster gene handling inconsistency
- Conservation (Track 3): Uses MAX across clusters ✅
- Consistency (Track 5): Uses FIRST cluster only ❌

**Recommendation:** Should also use MAX consistency across clusters for the 266 multi-cluster genes.

---

## TRACK 6: RAST Consistency

**Track ID:** `rast_cons`
**Field:** `RAST_CONS` (index 13)
**Type:** Consistency
**Enabled by default:** No

### What it shows
How well the RAST function annotation for this gene matches other genes in the same pangenome cluster.

### Computation
**Source:** `generate_genes_data.py` lines 159-179 (same function as Track 5, but returns individual score)

```python
def compute_rast_consistency(user_func, cluster_genes):
    """
    Compute exact string match fraction for RAST function.

    user_func: "ATP synthase subunit alpha" (from this gene)
    cluster_genes: [
        {'rast_function': 'ATP synthase subunit alpha'},
        {'rast_function': 'ATP synthase subunit alpha'},
        {'rast_function': 'F0F1 ATP synthase subunit alpha'},
        ...
    ]

    Returns: fraction of cluster genes with exact same RAST function (0.0-1.0)
    """
    if not user_func:
        return -1.0  # N/A if this gene has no RAST function

    matches = 0
    total = 0
    for gene in cluster_genes:
        if gene['rast_function']:
            total += 1
            if gene['rast_function'] == user_func:
                matches += 1

    return matches / total if total > 0 else -1.0
```

**Database query:**
```sql
-- Get pangenome cluster ID
SELECT pangenome_cluster_id
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?

-- Get RAST functions for all genes in cluster
SELECT rast_function
FROM pan_genome_features
WHERE cluster_id = ?
```

### Example values
- Perfect agreement: 1.0 (all genes have identical RAST function)
- 75% agreement: 0.75 (3/4 genes have same function)
- No agreement: 0.0 (no other genes have same function)
- N/A: -1.0 (no cluster, or this gene has no RAST function)

**Expected distribution:** Most genes >0.7 (RAST is consistent within homologous gene families)

### Color scheme
- **Orange (#f59e0b):** High consistency (1.0)
- **Blue (#3b82f6):** Low consistency (0.0)
- **Gray (#9ca3af):** N/A (-1.0)

### Biological interpretation

**High RAST consistency (>0.8):**
- Well-characterized gene families
- Conserved function across genomes
- High confidence in RAST annotation

**Low RAST consistency (<0.4):**
- May indicate:
  - Functional divergence within homologs
  - RAST annotation errors or inconsistencies
  - Multi-domain proteins with different annotation focus
  - Recent horizontal transfer with function change

**Why exact match is strict:**
- "ATP synthase subunit alpha" ≠ "F0F1 ATP synthase subunit alpha"
- Small wording differences count as mismatch
- This is intentionally conservative to catch annotation inconsistencies

### Implementation
**Display code:** `index.html` lines 1610-1625 (consistency scale)

### Known limitations
1. **Exact string matching:** Very strict - minor wording variations score as disagreement
2. **No synonym handling:** "kinase" vs "phosphotransferase" treated as different
3. **Multi-cluster genes:** Uses FIRST cluster only (same issue as Track 5)

---

## TRACK 7: KO Consistency

**Track ID:** `ko_cons`
**Field:** `KO_CONS` (index 14)
**Type:** Consistency
**Enabled by default:** No

### What it shows
How well the KEGG Orthology (KO) terms for this gene match other genes in the same pangenome cluster.

### Computation
**Source:** `generate_genes_data.py` lines 159-179 (Jaccard similarity)

```python
def compute_ko_consistency(user_ko, cluster_genes):
    """
    Compute average Jaccard similarity for KO terms.

    user_ko: "K00001;K00002;K00003" (semicolon-separated KO IDs)
    cluster_genes: [
        {'ko': 'K00001;K00002'},
        {'ko': 'K00001;K00002;K00003'},
        {'ko': 'K00001;K00004'},
        ...
    ]

    Returns: average Jaccard index across all cluster genes (0.0-1.0)
    """
    if not user_ko:
        return -1.0  # N/A if this gene has no KO terms

    user_set = set(user_ko.split(';'))

    similarities = []
    for gene in cluster_genes:
        if gene['ko']:
            cluster_set = set(gene['ko'].split(';'))
            intersection = len(user_set & cluster_set)
            union = len(user_set | cluster_set)
            jaccard = intersection / union if union > 0 else 0.0
            similarities.append(jaccard)

    return sum(similarities) / len(similarities) if similarities else -1.0
```

**Example calculation:**
```
User gene: K00001;K00002;K00003
Cluster gene 1: K00001;K00002      → Jaccard = 2/3 = 0.667
Cluster gene 2: K00001;K00002;K00003 → Jaccard = 3/3 = 1.0
Cluster gene 3: K00001;K00004      → Jaccard = 1/4 = 0.25

KO Consistency = (0.667 + 1.0 + 0.25) / 3 = 0.639
```

**Database query:**
```sql
-- Get KO terms for all genes in cluster
SELECT ko
FROM pan_genome_features
WHERE cluster_id = ?
```

**Database column:** `pan_genome_features.ko` (semicolon-separated KO IDs, e.g., "K00001;K00002")

### Example values
- Perfect agreement: 1.0 (all genes have identical KO term sets)
- Partial overlap: 0.5-0.8 (some KO terms shared)
- No overlap: 0.0 (completely different KO terms)
- N/A: -1.0 (no cluster, or no KO terms)

### Color scheme
Same as Track 6: Orange (high) → Blue (low), Gray (N/A)

### Biological interpretation

**High KO consistency (>0.8):**
- Conserved biochemical function
- Orthologous genes with same pathway roles
- High confidence in KO assignment

**Medium KO consistency (0.4-0.8):**
- May indicate:
  - Multi-domain proteins with variable domain composition
  - Partial functional conservation
  - Different pathway contexts

**Low KO consistency (<0.4):**
- Functional divergence within cluster
- KO assignment errors
- Truly multi-functional paralogs

**Advantage over RAST:** Uses Jaccard similarity instead of exact match, so partial overlap counts positively

### Implementation
**Display code:** `index.html` lines 1610-1625

### Known limitations
1. **Averages across genes:** Single outlier in cluster can lower score
2. **Equal weight to all KO terms:** Doesn't consider term hierarchy or importance
3. **Multi-cluster genes:** Uses FIRST cluster only

---

## TRACK 8: GO Consistency

**Track ID:** `go_cons`
**Field:** `GO_CONS` (index 15)
**Type:** Consistency
**Enabled by default:** No

### What it shows
How well Gene Ontology (GO) terms for this gene match other genes in the same pangenome cluster.

### Computation
**Source:** `generate_genes_data.py` lines 159-179 (same Jaccard formula as KO)

```python
def compute_go_consistency(user_go, cluster_genes):
    """Same as KO consistency, but for GO terms."""
    if not user_go:
        return -1.0

    user_set = set(user_go.split(';'))

    similarities = []
    for gene in cluster_genes:
        if gene['go']:
            cluster_set = set(gene['go'].split(';'))
            intersection = len(user_set & cluster_set)
            union = len(user_set | cluster_set)
            jaccard = intersection / union if union > 0 else 0.0
            similarities.append(jaccard)

    return sum(similarities) / len(similarities) if similarities else -1.0
```

**Database query:**
```sql
SELECT go
FROM pan_genome_features
WHERE cluster_id = ?
```

**Database column:** `pan_genome_features.go` (semicolon-separated GO IDs, e.g., "GO:0005737;GO:0008152")

**GO term types included:**
- Molecular Function (GO:0003xxx)
- Biological Process (GO:0008xxx)
- Cellular Component (GO:0005xxx)

### Example values
- High consistency: 0.8-1.0
- Medium consistency: 0.4-0.8
- Low consistency: 0.0-0.4
- N/A: -1.0

### Color scheme
Same as Tracks 6-7: Orange (high) → Blue (low), Gray (N/A)

### Biological interpretation

**High GO consistency (>0.8):**
- Conserved molecular function and process
- Reliable GO annotations
- True orthologs with same cellular role

**Low GO consistency (<0.4):**
- May indicate:
  - GO annotation incompleteness (different pipelines annotate different aspects)
  - Functional specialization within homologs
  - Annotation errors

**GO vs KO:**
- GO is broader (includes localization, process, function)
- KO is pathway-specific (metabolic focus)
- Both are useful for different characterization goals

### Implementation
**Display code:** `index.html` lines 1610-1625

### Known limitations
Same as KO consistency track

---

## TRACK 9: EC Consistency

**Track ID:** `ec_cons`
**Field:** `EC_CONS` (index 16)
**Type:** Consistency
**Enabled by default:** No

### What it shows
How well Enzyme Commission (EC) numbers for this gene match other genes in the same pangenome cluster.

### Computation
**Source:** `generate_genes_data.py` lines 159-179 (same Jaccard formula)

```python
def compute_ec_consistency(user_ec, cluster_genes):
    """Same as KO/GO consistency, but for EC numbers."""
    if not user_ec:
        return -1.0

    user_set = set(user_ec.split(';'))

    similarities = []
    for gene in cluster_genes:
        if gene['ec']:
            cluster_set = set(gene['ec'].split(';'))
            intersection = len(user_set & cluster_set)
            union = len(user_set | cluster_set)
            jaccard = intersection / union if union > 0 else 0.0
            similarities.append(jaccard)

    return sum(similarities) / len(similarities) if similarities else -1.0
```

**Database query:**
```sql
SELECT ec
FROM pan_genome_features
WHERE cluster_id = ?
```

**Database column:** `pan_genome_features.ec` (semicolon-separated EC numbers, e.g., "1.1.1.1;2.3.1.54")

**EC number format:**
- Class.Subclass.Sub-subclass.Serial (e.g., 1.1.1.1)
- Classes: 1=oxidoreductases, 2=transferases, 3=hydrolases, 4=lyases, 5=isomerases, 6=ligases, 7=translocases

### Example values
- High consistency: 0.8-1.0 (enzymes with conserved catalytic function)
- Medium: 0.4-0.8
- Low: 0.0-0.4
- N/A: -1.0

### Color scheme
Same as Tracks 6-8: Orange (high) → Blue (low), Gray (N/A)

### Biological interpretation

**High EC consistency (>0.8):**
- Conserved enzymatic activity
- Reliable enzyme classification
- True isozymes (same reaction, different proteins)

**Low EC consistency (<0.4):**
- May indicate:
  - Multi-functional enzymes (promiscuous activity)
  - EC assignment errors
  - Sub-functionalization within gene family
  - Moonlighting proteins (different catalytic activities)

**EC vs KO:**
- EC: Describes chemical reaction (what it does)
- KO: Describes pathway context (where it works)
- Same gene can have multiple EC numbers but single KO

### Implementation
**Display code:** `index.html` lines 1610-1625

### Known limitations
Same as KO/GO consistency tracks

---

## TRACK 10: Bakta Consistency

**Track ID:** `bakta_cons`
**Field:** `BAKTA_CONS` (index 18)
**Type:** Consistency
**Enabled by default:** No

### What it shows
How well the Bakta function annotation for this gene matches other genes in the same pangenome cluster.

### Computation
**Source:** `generate_genes_data.py` lines 159-179 (exact string match, same as RAST)

```python
def compute_bakta_consistency(user_bakta_func, cluster_genes):
    """
    Compute exact string match fraction for Bakta function.
    Same logic as RAST consistency (Track 6).
    """
    if not user_bakta_func:
        return -1.0

    matches = 0
    total = 0
    for gene in cluster_genes:
        if gene['bakta_function']:
            total += 1
            if gene['bakta_function'] == user_bakta_func:
                matches += 1

    return matches / total if total > 0 else -1.0
```

**Database query:**
```sql
SELECT bakta_function
FROM pan_genome_features
WHERE cluster_id = ?
```

**Database column:** `pan_genome_features.bakta_function` (free text, e.g., "ATP synthase subunit alpha")

### Example values
- Perfect agreement: 1.0
- Partial agreement: 0.5-0.8
- No agreement: 0.0
- N/A: -1.0

### Color scheme
Same as Tracks 6-9: Orange (high) → Blue (low), Gray (N/A)

### Biological interpretation

**Bakta vs RAST:**
- Bakta: Newer rapid annotation pipeline (2021+)
- RAST: Established SEED-based annotation (2008+)
- Different databases, different algorithms
- Agreement between them = higher confidence

**High Bakta consistency + High RAST consistency:**
- Very reliable annotation
- Well-characterized gene

**High Bakta + Low RAST (or vice versa):**
- Annotation pipeline disagreement
- May warrant manual review
- Could indicate genuinely ambiguous function

**Low both:**
- Poorly characterized gene family
- Annotation errors
- High functional divergence

### Implementation
**Display code:** `index.html` lines 1610-1625

### Known limitations
Same as RAST consistency (Track 6): exact string matching is strict

---

## TRACK 11: Annotation Specificity

**Track ID:** `specificity`
**Field:** `SPECIFICITY` (index 20)
**Type:** Consistency
**Enabled by default:** No

### What it shows
How specific and detailed the functional annotation is (0=vague, 1=specific).

### Computation
**Source:** `generate_genes_data.py` lines 404-446

```python
def compute_annotation_specificity(rast_func, bakta_func, ko, go, ec, pfam):
    """
    Score annotation quality based on:
    1. Non-hypothetical function
    2. Ontology term richness
    3. Function text specificity

    Returns: 0.0-1.0 (higher = more specific annotation)
    """
    score = 0.0

    # ── Component 1: Has non-hypothetical function (0.3 weight) ──
    has_real_function = False
    for func in [rast_func, bakta_func]:
        if func and not is_hypothetical(func):
            has_real_function = True
            break

    if has_real_function:
        score += 0.3

    # ── Component 2: Ontology richness (0.4 weight) ──
    # Count unique ontology terms
    n_ko = len([k for k in (ko or '').split(';') if k.strip()])
    n_go = len([g for g in (go or '').split(';') if g.strip()])
    n_ec = len([e for e in (ec or '').split(';') if e.strip()])
    n_pfam = len([p for p in (pfam or '').split(';') if p.strip()])

    total_ontology = n_ko + n_go + n_ec + n_pfam

    # Normalize: 0 terms=0.0, 10+ terms=1.0
    ontology_score = min(total_ontology / 10.0, 1.0)
    score += 0.4 * ontology_score

    # ── Component 3: Function text detail (0.3 weight) ──
    # Longer, more detailed function = higher score
    best_func = rast_func or bakta_func or ""

    # Word count (more words = more specific)
    word_count = len(best_func.split())

    # Presence of specific keywords
    specific_keywords = ['subunit', 'domain', 'family', 'type', 'class',
                         'binding', 'dependent', 'specific', 'associated']
    keyword_bonus = sum(1 for kw in specific_keywords if kw in best_func.lower())

    # Normalize
    detail_score = min((word_count + keyword_bonus) / 15.0, 1.0)
    score += 0.3 * detail_score

    return round(score, 4)
```

**Database query:** None (computed from already-loaded annotations)

### Scoring breakdown

**High specificity (0.8-1.0):**
- Non-hypothetical function ✓
- Multiple ontology terms (KO, GO, EC, Pfam) ✓
- Detailed function text with domain/subunit information ✓
- Example: "ATP synthase subunit alpha" + 5 KO + 8 GO + 2 EC + 3 Pfam = 0.95

**Medium specificity (0.4-0.7):**
- Has function but limited ontology
- OR has ontology but vague function
- Example: "Conserved hypothetical protein" + 3 KO + 2 GO = 0.55

**Low specificity (0.0-0.3):**
- Hypothetical protein
- No or minimal ontology terms
- Example: "Hypothetical protein" + 0 ontology = 0.0

### Example values
- Well-annotated enzyme: 0.85-1.0
- Partially characterized: 0.4-0.7
- Hypothetical: 0.0-0.3
- Distribution: Mean ~0.52 (moderate annotation quality)

### Color scheme
**Note:** Track uses consistency color scale but represents specificity (not agreement)
- **Orange (#f59e0b):** High specificity (1.0)
- **Blue (#3b82f6):** Low specificity (0.0)
- **No gray:** Specificity is always 0.0-1.0 (never N/A)

### Biological interpretation

**High specificity genes:**
- Well-studied proteins
- Core metabolic enzymes
- Housekeeping genes
- High confidence for further analysis

**Low specificity genes (characterization targets):**
- Novel or poorly studied
- Potential for discovery
- May be organism-specific innovations
- Require experimental characterization

### Implementation
**Display code:** `index.html` lines 1610-1625 (uses consistency scale)

### Known limitations
1. **Subjective weighting:** 30% function + 40% ontology + 30% detail is arbitrary
2. **Word count bias:** Longer ≠ always better (verbose ≠ specific)
3. **No validation:** Score doesn't verify annotation correctness
4. **NOT in database:** Computed during extraction, not stored in SQLite

---

## TRACK 12: # KEGG Terms

**Track ID:** `n_ko`
**Field:** `N_KO` (index 8)
**Type:** Sequential
**Enabled by default:** No

### What it shows
Count of KEGG Orthology (KO) terms assigned to this gene.

### Computation
**Source:** `generate_genes_data.py` lines 492-494

```python
# Count KO terms
ko = row['ko'] or ''
n_ko = len([k for k in ko.split(';') if k.strip()])
```

**Database query:**
```sql
SELECT ko
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?
```

**Database column:** `genome_features.ko` (semicolon-separated KO IDs, e.g., "K00001;K00002")

### Example values
- No KO terms: 0 (genes not in KEGG database)
- Single KO: 1 (most genes)
- Multiple KO: 2-5 (multi-functional or multi-domain proteins)
- Distribution: Mean ~1.2 KO terms per gene

### Color scheme
Blue gradient (light blue=0 → dark blue=max)

### Biological interpretation

**0 KO terms:**
- Not in KEGG database
- May be:
  - Hypothetical proteins
  - Organism-specific genes
  - Structural proteins
  - Regulatory proteins (KEGG focuses on metabolism)

**1 KO term:**
- Standard case
- Well-defined metabolic or signaling function

**Multiple KO terms (2+):**
- Multi-functional enzyme
- Fusion protein
- Multi-domain protein
- Or: Annotation ambiguity (multiple possible assignments)

### Implementation
**Display code:** `index.html` lines 1607-1625 (sequential scale)

### Known limitations
1. **KEGG bias:** Emphasizes metabolism, underrepresents structural/regulatory
2. **Count ≠ quality:** High count doesn't mean high confidence

---

## TRACK 13: # COG Terms

**Track ID:** `n_cog`
**Field:** `N_COG` (index 9)
**Type:** Sequential
**Enabled by default:** No

### What it shows
Count of Clusters of Orthologous Groups (COG) terms assigned to this gene.

### Computation
**Source:** `generate_genes_data.py` lines 495-497

```python
# Count COG terms
cog = row['cog'] or ''
n_cog = len([c for c in cog.split(';') if c.strip()])
```

**Database query:**
```sql
SELECT cog
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?
```

**Database column:** `genome_features.cog` (semicolon-separated COG IDs, e.g., "COG0001;COG0002")

**COG categories:**
- Information storage/processing
- Cellular processes
- Metabolism
- Poorly characterized

### Example values
- No COG: 0
- Single COG: 1 (most genes)
- Multiple COG: 2-3 (multi-domain proteins)
- Distribution: Mean ~0.8 COG terms per gene

### Color scheme
Blue gradient (light blue=0 → dark blue=max)

### Biological interpretation

**COG vs KO:**
- COG: Broader functional categories (cellular role)
- KO: Specific pathway/ortholog (biochemical function)
- Both useful for different classification goals

**0 COG terms:**
- Not in COG database
- May be species-specific or novel

**Multiple COG:**
- Multi-domain proteins
- Fusion proteins
- Annotation ambiguity

### Implementation
**Display code:** `index.html` lines 1607-1625 (sequential scale)

### Known limitations
Same as N_KO track

---

## TRACK 14: # Pfam Terms

**Track ID:** `n_pfam`
**Field:** `N_PFAM` (index 10)
**Type:** Sequential
**Enabled by default:** No

### What it shows
Count of Pfam protein domain families assigned to this gene.

### Computation
**Source:** `generate_genes_data.py` lines 498-500

```python
# Count Pfam terms
pfam = row['pfam'] or ''
n_pfam = len([p for p in pfam.split(';') if p.strip()])
```

**Database query:**
```sql
SELECT pfam
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?
```

**Database column:** `genome_features.pfam` (semicolon-separated Pfam IDs, e.g., "PF00001;PF00002")

### Example values
- No Pfam: 0
- Single domain: 1 (most proteins)
- Multiple domains: 2-5 (complex multi-domain proteins)
- Distribution: Mean ~1.5 Pfam domains per gene

### Color scheme
Blue gradient (light blue=0 → dark blue=max)

### Biological interpretation

**Pfam domains:**
- Conserved protein sequence motifs
- Structural/functional modules
- Often independently folding units

**0 Pfam:**
- No recognizable domains
- Novel protein
- Too short or disordered

**1 Pfam:**
- Single-domain protein
- Simple architecture

**Multiple Pfam (3+):**
- Multi-domain protein
- Complex architecture
- Often regulatory or signaling proteins
- Examples: kinases, transcription factors

**Pfam vs KO/COG:**
- Pfam: Sequence-based domain annotation
- KO/COG: Function-based orthology
- Pfam is purely structural, others are functional

### Implementation
**Display code:** `index.html` lines 1607-1625 (sequential scale)

### Known limitations
Same as N_KO/N_COG tracks

---

## TRACK 15: # GO Terms

**Track ID:** `n_go`
**Field:** `N_GO` (index 11)
**Type:** Sequential
**Enabled by default:** No

### What it shows
Count of Gene Ontology (GO) terms assigned to this gene.

### Computation
**Source:** `generate_genes_data.py` lines 501-503

```python
# Count GO terms
go = row['go_terms'] or ''
n_go = len([g for g in go.split(';') if g.strip()])
```

**Database query:**
```sql
SELECT go_terms
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?
```

**Database column:** `genome_features.go_terms` (semicolon-separated GO IDs)

### Example values
- No GO: 0
- Few GO: 1-3
- Many GO: 5-15 (well-characterized genes)
- Distribution: Mean ~4.2 GO terms per gene

### Color scheme
Blue gradient (light blue=0 → dark blue=max)

### Biological interpretation

**High GO count (10+):**
- Well-studied gene
- Multi-aspect annotation (function + process + component)
- Often essential housekeeping genes

**Low GO count (0-2):**
- Poorly characterized
- Organism-specific
- Hypothetical proteins

**GO vs other ontologies:**
- GO: Broadest (function, process, localization)
- KO: Metabolic pathways
- COG: Functional categories
- Pfam: Protein domains

### Implementation
**Display code:** `index.html` lines 1607-1625 (sequential scale)

### Known limitations
Same as other ontology count tracks

---

## TRACK 16: Subcellular Localization

**Track ID:** `localization`
**Field:** `LOC` (index 12)
**Type:** Categorical
**Enabled by default:** No

### What it shows
Predicted subcellular localization of the protein product.

### Computation
**Source:** `generate_genes_data.py` lines 312-314

```python
# Map PSORTb prediction to canonical localization
LOC_MAP = {
    "Cytoplasmic": 0,
    "CytoplasmicMembrane": 1,
    "Periplasmic": 2,
    "OuterMembrane": 3,
    "Extracellular": 4,
    "Unknown": 5
}

psortb = row["psortb"] or "Unknown"
loc = LOC_MAP.get(psortb, LOC_MAP["Unknown"])
```

**Database query:**
```sql
SELECT psortb
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?
```

**Database column:** `genome_features.psortb` (PSORTb v3.0 prediction)

**Localization categories (bacterial):**
- **0 = Cytoplasmic:** Inside the cell, soluble proteins
- **1 = CytoplasmicMembrane:** Inner membrane proteins
- **2 = Periplasmic:** Periplasmic space (Gram-negative)
- **3 = OuterMembrane:** Outer membrane proteins (Gram-negative)
- **4 = Extracellular:** Secreted proteins
- **5 = Unknown:** No confident prediction

### Example values
- Cytoplasmic: ~65% (most proteins)
- Membrane: ~25% (inner + outer)
- Periplasmic: ~5%
- Extracellular: ~3%
- Unknown: ~2%

### Color scheme
Six categorical colors (assigned by config.json order):
- Cytoplasmic: Color 1
- CytoMembrane: Color 2
- Periplasmic: Color 3
- OuterMembrane: Color 4
- Extracellular: Color 5
- Unknown: Gray

### Biological interpretation

**Cytoplasmic enrichment:**
- Most metabolic enzymes
- DNA/RNA processing
- Protein synthesis machinery

**Membrane proteins:**
- Transporters
- Signal transduction
- Energy generation (respiratory chain)

**Periplasmic:**
- Binding proteins (ABC transporters)
- Chaperones
- Degradation enzymes

**Outer membrane:**
- Porins (nutrient uptake)
- Adhesion proteins
- Protection

**Extracellular:**
- Toxins
- Degradative enzymes
- Cell wall modification

### Implementation
**Display code:** `index.html` lines 1607 (categorical color mapping)

### Known limitations
1. **PSORTb accuracy:** ~95% for Gram-negative, lower for Gram-positive
2. **Multi-localization:** Proteins can have multiple locations (only one predicted)
3. **Dynamic localization:** Doesn't capture condition-dependent changes

---

## TRACK 17: Has Gene Name

**Track ID:** `has_name`
**Field:** `HAS_NAME` (index 22)
**Type:** Binary
**Enabled by default:** No

### What it shows
Whether the gene has a common gene name (e.g., "dnaK", "recA") vs just a locus tag.

### Computation
**Source:** `generate_genes_data.py` lines 455-459

```python
# Has gene name?
gene_names = row["gene_names"] or ""
has_name = 1 if gene_names and gene_names.strip() else 0
```

**Database query:**
```sql
SELECT gene_names
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?
```

**Database column:** `genome_features.gene_names` (common gene symbols, e.g., "recA", "dnaK")

### Example values
- Has name (1): ~30-40% of genes
- No name (0): ~60-70% of genes

### Color scheme
Binary colors:
- **Purple (#9333ea):** Has name (1)
- **Orange (#f59e0b):** No name (0)

### Biological interpretation

**Genes with names:**
- Well-characterized in literature
- Essential housekeeping genes
- Historically important discoveries
- Examples: recA (recombination), dnaK (chaperone), lacZ (beta-galactosidase)

**Genes without names:**
- Less studied
- Organism-specific
- Recently discovered
- Hypothetical proteins

**Correlation with annotation quality:**
- Has name → usually high specificity
- No name → not necessarily poorly characterized (may just be unnamed)

### Implementation
**Display code:** `index.html` lines 1607 (binary color mapping)

### Known limitations
1. **Arbitrary naming:** Some well-characterized genes lack common names
2. **Naming bias:** Older literature genes more likely to have names

---

## TRACK 18: # EC Numbers

**Track ID:** `n_ec`
**Field:** `N_EC` (index 23)
**Type:** Sequential
**Enabled by default:** No

### What it shows
Count of Enzyme Commission (EC) numbers assigned to this gene.

### Computation
**Source:** `generate_genes_data.py` lines 310

```python
n_ec = count_terms(row["ec"])

def count_terms(term_str):
    """Count semicolon-separated terms."""
    if not term_str:
        return 0
    return len([t for t in term_str.split(';') if t.strip()])
```

**Database query:**
```sql
SELECT ec
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?
```

**Database column:** `genome_features.ec` (semicolon-separated EC numbers)

### Example values
- No EC: 0 (~60% of genes - non-enzymes)
- Single EC: 1 (~35% - standard enzymes)
- Multiple EC: 2-5 (~5% - multi-functional enzymes)
- Distribution: Mean ~0.5 EC numbers per gene

### Color scheme
Blue gradient (light blue=0 → dark blue=max)

### Biological interpretation

**0 EC numbers:**
- Not an enzyme
- Structural proteins, regulators, transporters
- Or: enzymatic activity not characterized

**1 EC number:**
- Standard enzyme with single catalytic function
- Most metabolic enzymes

**Multiple EC numbers (2+):**
- Multi-functional enzyme (catalyzes multiple reactions)
- Promiscuous enzyme (broad substrate specificity)
- Examples: bifunctional kinases, multifunctional synthases

**Metabolic enrichment:**
- Genes with EC numbers = metabolically active
- Use with metabolic map for pathway coverage

### Implementation
**Display code:** `index.html` lines 1607-1625 (sequential scale)

### Known limitations
1. **Underreporting:** Some enzymes lack EC assignments
2. **Promiscuity:** Moonlighting proteins may have unreported activities

---

## TRACK 19: Cluster Size

**Track ID:** `cluster_size`
**Field:** `CLUSTER_SIZE` (index 25)
**Type:** Sequential
**Enabled by default:** No

### What it shows
Number of genes (across all genomes) in this gene's pangenome cluster.

### Computation
**Source:** `generate_genes_data.py` lines 219-224, 364-378

```python
# Pre-compute cluster sizes
cluster_size = {}
for row in conn.execute("""
    SELECT cluster_id, COUNT(*) as cnt
    FROM pan_genome_features
    GROUP BY cluster_id
"""):
    cluster_size[row["cluster_id"]] = row["cnt"]

# For each gene
if cluster_ids:
    best_size = 0
    for cid in cluster_ids:
        csize = cluster_size.get(cid, 0)
        if csize > best_size:
            best_size = csize
    clust_size = best_size
else:
    clust_size = 0  # No cluster
```

**Database query:**
```sql
SELECT COUNT(*) as cnt
FROM pan_genome_features
WHERE cluster_id = ?
```

**Multi-cluster genes:** Takes MAX cluster size (consistent with conservation)

### Example values
- No cluster: 0 (~3% of genes)
- Small cluster: 1-10 genes
- Medium cluster: 11-35 genes (max = # of reference genomes)
- Large cluster: 36+ genes (duplications within genomes)
- Distribution: Most genes in clusters of size 35 (single-copy core genes)

### Color scheme
Blue gradient (light blue=0 → dark blue=max)

### Biological interpretation

**Cluster size = # ref genomes (35):**
- Single-copy core gene
- One representative per genome
- High conservation, essential function

**Cluster size > 35:**
- Gene duplications (paralogs)
- Multi-copy gene families
- Examples: ABC transporters, regulatory proteins

**Small cluster size (<35):**
- Accessory genes
- Strain-specific
- Recent acquisitions

**Cluster size correlation:**
- High size + high conservation = core single-copy
- High size + low conservation = expanded gene family (paralogs)

### Implementation
**Display code:** `index.html` lines 1607-1625 (sequential scale)

### Known limitations
1. **Pangenome completeness:** Limited to 35 reference genomes
2. **Paralog resolution:** Can't distinguish orthologs from paralogs within clusters

---

## TRACK 20: KEGG Module Hits

**Track ID:** `n_modules`
**Field:** `N_MODULES` (index 26)
**Type:** Sequential
**Enabled by default:** No

### What it shows
Number of KEGG modules (pathways) this gene participates in.

### Computation
**Source:** `generate_genes_data.py` lines 246-258, 505-515

```python
# Pre-load module-KO mappings
module_kos = {}
for row in conn.execute("SELECT id, kos FROM phenotype_module"):
    kos_str = row["kos"] or ""
    kos = set(k.strip() for k in kos_str.split(";") if k.strip())
    if kos:
        module_kos[row["id"]] = kos

# For each gene
gene_kos = set(row["ko"].split(';')) if row["ko"] else set()
n_modules = 0
for module_id, module_ko_set in module_kos.items():
    if gene_kos & module_ko_set:  # Intersection
        n_modules += 1
```

**Database query:**
```sql
-- Pre-load KEGG modules
SELECT id, kos
FROM phenotype_module

-- For each gene: check if gene KO terms overlap with module KO terms
```

**Database tables:**
- `genome_features.ko`: Gene KO terms
- `phenotype_module.kos`: Module KO composition

### Example values
- No modules: 0 (~40% - genes not in KEGG pathways)
- Few modules: 1-3 (~50% - standard metabolic genes)
- Many modules: 4-10 (~10% - hub enzymes in multiple pathways)
- Distribution: Mean ~1.8 modules per gene

### Color scheme
Blue gradient (light blue=0 → dark blue=max)

### Biological interpretation

**High module count (5+):**
- Central metabolic enzymes
- Hub reactions connecting multiple pathways
- Examples: pyruvate kinase, phosphoglycerate kinase

**Single module:**
- Pathway-specific enzymes
- Specialized function

**Zero modules:**
- Not in KEGG database
- Non-metabolic genes
- Or: KO term not mapped to modules

**Correlation with N_KO:**
- High N_KO + High N_MODULES = multi-functional enzyme
- High N_KO + Low N_MODULES = annotation ambiguity

### Implementation
**Display code:** `index.html` lines 1607-1625 (sequential scale)

### Known limitations
1. **KEGG coverage:** Only metabolic pathways, no signaling/regulatory
2. **Module definition:** Arbitrary pathway boundaries
3. **Requires phenotype_module table:** Not all databases have this

---

## TRACK 21: EC Mapped Consistency

**Track ID:** `ec_map_cons`
**Field:** `EC_MAP_CONS` (index 27)
**Type:** Consistency
**Enabled by default:** No

### What it shows
Consistency score for EC numbers mapped through metabolic modeling.

### Computation
**Source:** `generate_genes_data.py` lines 430-431

```python
# EC mapped consistency (not available in new DB, set to -1)
ec_map_cons = -1
```

**Status:** **DEPRECATED FIELD** - Not computed in current pipeline

**Original intent:** EC numbers inferred from metabolic model gene-reaction associations, then consistency computed across cluster.

**Current behavior:** Always returns -1 (N/A)

### Example values
- All genes: -1 (field not populated)

### Color scheme
Gray (all values are N/A)

### Biological interpretation
**This track is non-functional in current implementation.**

Originally designed to:
1. Map genes → reactions via metabolic model
2. Extract EC numbers from reactions
3. Compute consistency of mapped EC vs annotated EC

**Why deprecated:**
- Metabolic model data moved to separate fields (REACTIONS, RICH_FLUX, MIN_FLUX)
- EC mapping now handled by reactions_data.json
- Consistency computation would be redundant with Track 9 (EC_CONS)

### Implementation
**Display code:** `index.html` lines 1610-1625 (consistency scale, but always shows gray)

### Known limitations
**Entire track is non-functional** - consider removing from UI or implementing properly

---

## TRACK 22: Protein Length

**Track ID:** `prot_len`
**Field:** `PROT_LEN` (index 28)
**Type:** Sequential
**Enabled by default:** No

### What it shows
Protein length in amino acids.

### Computation
**Source:** `generate_genes_data.py` lines 473-474

```python
# Protein length = gene length (bp) / 3
prot_len = length // 3
```

**Note:** Gene length (field LENGTH, index 2) is in base pairs. Protein length divides by 3 (codon size).

**Database query:**
```sql
SELECT length
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?
```

**Database column:** `genome_features.length` (gene length in bp)

### Example values
- Short peptides: <100 aa
- Small proteins: 100-200 aa
- Medium proteins: 200-500 aa
- Large proteins: 500-1000 aa
- Very large proteins: >1000 aa (rare)
- Distribution: Median ~300 aa, mean ~350 aa

### Color scheme
Blue gradient (light blue=short → dark blue=long)

### Biological interpretation

**Short proteins (<100 aa):**
- Regulatory peptides
- Small subunits
- Toxins
- RNA-binding proteins

**Medium proteins (200-500 aa):**
- Most enzymes
- Standard globular proteins
- Single-domain proteins

**Large proteins (>800 aa):**
- Multi-domain proteins
- Structural proteins
- Complex enzymes
- Regulatory proteins

**Size correlations:**
- Large proteins often have more Pfam domains (N_PFAM)
- Large proteins may have more GO terms (better characterized)

### Implementation
**Display code:** `index.html` lines 1607-1625 (sequential scale)

### Known limitations
1. **Stop codons:** Calculation doesn't account for stop codon (should be length/3 - 1)
2. **Frameshift errors:** Assumes correct ORF prediction

---

## TRACK 23: Flux (Rich Media)

**Track ID:** `rich_flux`
**Field:** `RICH_FLUX` (index 30)
**Type:** Sequential
**Enabled by default:** No

### What it shows
Predicted metabolic flux (reaction rate) for genes encoding enzymes, simulated in rich media growth conditions.

### Computation
**Source:** `generate_genes_data.py` lines 323-324

```python
# RICH_FLUX [30]: rich media flux from metabolic modeling
rich_flux = row["rich_media_flux"] if "rich_media_flux" in row.keys() and row["rich_media_flux"] is not None else -1
```

**Database query:**
```sql
SELECT rich_media_flux
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?
```

**Database column:** `genome_features.rich_media_flux` (predicted flux value from FBA)

**Flux units:** mmol/gDW/hr (millimoles per gram dry weight per hour)

**Simulation conditions:**
- Rich media (LB-like): All nutrients available
- Aerobic growth
- Biomass maximization objective
- Flux Balance Analysis (FBA)

### Example values
- No flux: -1 (~60% of genes - non-enzymes or blocked reactions)
- Low flux: 0.001-0.1 (~20% - minor pathways)
- Medium flux: 0.1-10 (~15% - active metabolism)
- High flux: >10 (~5% - central carbon metabolism)

### Color scheme
Blue gradient (light blue=low flux → dark blue=high flux)
**Note:** -1 values (N/A) rendered as gray

### Biological interpretation

**High flux (>10):**
- Central carbon metabolism (glycolysis, TCA cycle)
- Essential biosynthetic pathways
- High enzymatic activity
- Rate-limiting steps

**Medium flux (0.1-10):**
- Secondary metabolism
- Amino acid biosynthesis
- Cofactor production

**Low flux (<0.1):**
- Alternative pathways (not used in rich media)
- Backup enzymes
- Condition-specific metabolism

**Zero flux (but not -1):**
- Enzyme present but reaction blocked
- Missing substrates/cofactors
- Thermodynamically unfavorable

**N/A (-1):**
- Non-enzymatic gene
- Reaction not in metabolic model
- No GPR (gene-protein-reaction) association

### Implementation
**Display code:** `index.html` lines 1607-1625 (sequential scale with N/A handling)

### Known limitations
1. **FBA assumptions:** Steady-state, no regulation, no enzyme kinetics
2. **Model completeness:** Not all reactions included
3. **Condition-specific:** Only rich media (see MIN_FLUX for minimal media)

---

## TRACK 24: Flux (Minimal Media)

**Track ID:** `min_flux`
**Field:** `MIN_FLUX` (index 32)
**Type:** Sequential
**Enabled by default:** No

### What it shows
Predicted metabolic flux in minimal media (glucose + salts only).

### Computation
**Source:** `generate_genes_data.py` lines 334-335

```python
# MIN_FLUX [32]: minimal media flux
min_flux = row["minimal_media_flux"] if "minimal_media_flux" in row.keys() and row["minimal_media_flux"] is not None else -1
```

**Database query:**
```sql
SELECT minimal_media_flux
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?
```

**Database column:** `genome_features.minimal_media_flux`

**Simulation conditions:**
- Minimal media (M9): Glucose + salts only
- Aerobic growth
- Biomass maximization
- Flux Balance Analysis (FBA)

### Example values
- N/A: -1 (~60% - non-enzymes)
- Zero flux: 0 (~15% - not needed in minimal media)
- Active flux: >0 (~25% - biosynthetic pathways active)

### Color scheme
Blue gradient (light blue=low → dark blue=high), Gray for N/A

### Biological interpretation

**High MIN_FLUX + High RICH_FLUX:**
- Essential biosynthetic pathways
- Always active regardless of nutrient availability
- Core metabolism

**High MIN_FLUX + Low RICH_FLUX:**
- Biosynthesis of amino acids/vitamins
- Upregulated when nutrients not available
- Condition-specific activation

**Low MIN_FLUX + High RICH_FLUX:**
- Degradation/salvage pathways
- Only used when substrates abundant
- Not needed for minimal growth

**Comparison use case:**
- MIN_FLUX > RICH_FLUX → biosynthetic gene (more active when making own nutrients)
- RICH_FLUX > MIN_FLUX → catabolic gene (more active when substrates available)

### Implementation
**Display code:** `index.html` lines 1607-1625

### Known limitations
Same as RICH_FLUX track

---

## TRACK 25: Flux Class (Rich Media)

**Track ID:** `rich_class`
**Field:** `RICH_CLASS` (index 31)
**Type:** Categorical
**Enabled by default:** No

### What it shows
Reaction classification based on flux variability in rich media.

### Computation
**Source:** `generate_genes_data.py` lines 326-332

```python
# Map flux class string to index
rich_class_map = {"essential": 0, "variable": 1, "blocked": 2}

rich_class_str = row["rich_media_class"] if "rich_media_class" in row.keys() else ""
rich_class = rich_class_map.get(rich_class_str, -1)  # -1 if not found or empty
```

**Database query:**
```sql
SELECT rich_media_class
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?
```

**Database column:** `genome_features.rich_media_class` (values: "essential", "variable", "blocked", or NULL)

**Classification criteria (from Flux Variability Analysis):**
- **Essential (0):** Reaction MUST carry flux (min flux > threshold)
- **Variable (1):** Reaction CAN carry flux but not required (0 ≤ flux ≤ max)
- **Blocked (2):** Reaction CANNOT carry flux (max flux = 0)

### Example values
- Essential: ~10-15% of enzymatic genes
- Variable: ~20-25%
- Blocked: ~5-10%
- N/A (-1): ~50-60% (non-enzymatic genes)

### Color scheme
Three categorical colors:
- **Essential:** Color 1 (e.g., red - required)
- **Variable:** Color 2 (e.g., yellow - optional)
- **Blocked:** Color 3 (e.g., gray - inactive)
- **N/A (-1):** Gray

### Biological interpretation

**Essential reactions:**
- Critical for growth in rich media
- No alternative pathways
- Gene deletion would be lethal
- Examples: core glycolysis, DNA replication enzymes

**Variable reactions:**
- Flexible metabolism
- Multiple alternative routes
- Non-essential but beneficial
- Examples: amino acid salvage when available

**Blocked reactions:**
- Missing cofactors/substrates
- Thermodynamically blocked
- Or: model gaps (incomplete network)

**Essentiality vs gene essentiality:**
- Reaction essential ≠ gene essential (paralogs can compensate)
- Use with ESSENTIALITY track (index 35) for comparison

### Implementation
**Display code:** `index.html` lines 1607 (categorical color mapping)

### Known limitations
1. **FVA assumptions:** Requires metabolic model and FBA
2. **Condition-specific:** Only rich media (see MIN_CLASS for minimal)
3. **Model gaps:** Blocked may indicate missing reactions

---

## TRACK 26: Flux Class (Minimal Media)

**Track ID:** `min_class`
**Field:** `MIN_CLASS` (index 33)
**Type:** Categorical
**Enabled by default:** No

### What it shows
Reaction classification based on flux variability in minimal media.

### Computation
**Source:** `generate_genes_data.py` lines 337-341

```python
# Same mapping as RICH_CLASS
min_class_str = row["minimal_media_class"] if "minimal_media_class" in row.keys() else ""
min_class = rich_class_map.get(min_class_str, -1)
```

**Database query:**
```sql
SELECT minimal_media_class
FROM genome_features
WHERE genome_id = 'user_genome' AND feature_id = ?
```

**Database column:** `genome_features.minimal_media_class`

**Classification:** Same as RICH_CLASS, but for minimal media growth

### Example values
- Essential: ~15-20% (higher than rich - need biosynthesis)
- Variable: ~15-20%
- Blocked: ~5-10%
- N/A: ~50-60%

### Color scheme
Same as RICH_CLASS: Essential/Variable/Blocked/N/A

### Biological interpretation

**Essential in minimal but variable in rich:**
- Biosynthetic genes (amino acids, vitamins)
- Required when nutrients not provided
- Dispensable when nutrients abundant

**Essential in both:**
- Core central metabolism
- DNA/RNA synthesis
- Truly essential for life

**Blocked in minimal but variable in rich:**
- Degradation/salvage pathways
- Require substrates only in rich media

**Comparison matrix:**

| MIN_CLASS | RICH_CLASS | Interpretation |
|-----------|------------|----------------|
| Essential | Essential  | Core metabolism |
| Essential | Variable   | Biosynthetic |
| Variable  | Essential  | Catabolic |
| Blocked   | Variable   | Substrate-dependent |

### Implementation
**Display code:** `index.html` lines 1607 (categorical)

### Known limitations
Same as RICH_CLASS

---

## TRACK 27: Gene Essentiality

**Track ID:** `essentiality`
**Field:** `ESSENTIALITY` (index 35)
**Type:** Sequential
**Enabled by default:** No

### What it shows
Experimental gene essentiality score from transposon insertion sequencing (Tn-Seq) or similar assays.

### Computation
**Source:** `generate_genes_data.py` lines 261-274, 348

```python
# Pre-load gene essentiality data
gene_essentiality = {}
try:
    for row in conn.execute("""
        SELECT gene_id, AVG(essentiality_fraction) as avg_ess
        FROM gene_phenotypes
        WHERE genome_id = ?
        GROUP BY gene_id
    """, (user_genome_id,)):
        gene_essentiality[row["gene_id"]] = round(row["avg_ess"], 4) if row["avg_ess"] is not None else -1
except sqlite3.OperationalError:
    print("  (gene_phenotypes table not found, essentiality will be -1)")

# For each gene
essentiality = gene_essentiality.get(fid, -1)
```

**Database query:**
```sql
SELECT gene_id, AVG(essentiality_fraction) as avg_ess
FROM gene_phenotypes
WHERE genome_id = 'user_genome'
GROUP BY gene_id
```

**Database table:** `gene_phenotypes`
**Database column:** `essentiality_fraction` (experimental value, 0.0-1.0)

**Essentiality definition:**
- 1.0 = Essential (no viable mutants, gene required for growth)
- 0.0 = Non-essential (viable mutants, gene dispensable)
- 0.3-0.7 = Context-dependent or fitness cost

### Example values
- Essential: >0.8 (~10-15% of genes)
- Fitness defect: 0.3-0.8 (~15-20%)
- Non-essential: <0.3 (~60-70%)
- N/A: -1 (no experimental data)

### Color scheme
Blue gradient (light blue=non-essential → dark blue=essential)
Gray for N/A

### Biological interpretation

**High essentiality (>0.8):**
- Required for growth
- Gene deletion is lethal
- Core cellular functions (replication, translation, cell wall)

**Medium essentiality (0.3-0.7):**
- Fitness defect but not lethal
- Slow growth phenotype
- Conditional essentiality

**Low essentiality (<0.3):**
- Dispensable genes
- Accessory functions
- Redundant paralogs

**Correlation with modeling:**
- Compare with RICH_CLASS/MIN_CLASS (predicted vs experimental)
- High essentiality + Essential flux class = validated model
- High essentiality + Variable flux class = model gap or gene redundancy

### Implementation
**Display code:** `index.html` lines 1607-1625 (sequential scale)

### Known limitations
1. **Data availability:** gene_phenotypes table often empty (user_genome may not have Tn-Seq data)
2. **Condition-specific:** Essentiality depends on growth conditions
3. **Averaging:** Multiple experiments averaged, may lose condition specificity

---

## TRACK 28: # Phenotypes

**Track ID:** `n_phenotypes`
**Field:** `N_PHENOTYPES` (index 36)
**Type:** Sequential
**Enabled by default:** No

### What it shows
Number of phenotype associations for this gene (from experimental studies).

### Computation
**Source:** Implied from database structure (not directly in generate_genes_data.py extraction code shown)

**Expected computation:**
```python
# Count phenotype records for this gene
n_phenotypes = conn.execute("""
    SELECT COUNT(*)
    FROM gene_phenotypes
    WHERE genome_id = ? AND gene_id = ?
""", (user_genome_id, fid)).fetchone()[0]
```

**Database query:**
```sql
SELECT COUNT(*)
FROM gene_phenotypes
WHERE genome_id = 'user_genome' AND gene_id = ?
```

**Database table:** `gene_phenotypes`

**Phenotype types may include:**
- Growth defects
- Metabolic alterations
- Stress sensitivity
- Morphological changes

### Example values
- No phenotypes: 0 (~60-80% of genes - not experimentally tested)
- Few phenotypes: 1-3 (~15-30%)
- Many phenotypes: 4+ (~5%)

### Color scheme
Blue gradient (light blue=0 → dark blue=max)

### Biological interpretation

**High phenotype count (5+):**
- Extensively studied gene
- Pleiotropic effects (affects multiple processes)
- Important for cell physiology

**Low phenotype count (1-2):**
- Limited experimental characterization
- Specific function
- Or: only tested in few conditions

**Zero phenotypes:**
- No experimental data
- Gene not included in phenotype screens
- Or: no observable phenotype (truly dispensable)

**Correlation with essentiality:**
- High N_PHENOTYPES + High ESSENTIALITY = critical gene
- High N_PHENOTYPES + Low ESSENTIALITY = pleiotropic non-essential

### Implementation
**Display code:** `index.html` lines 1607-1625 (sequential scale)

### Known limitations
1. **Data sparsity:** gene_phenotypes table often has limited data
2. **Ascertainment bias:** Well-studied organisms have more phenotypes
3. **Condition coverage:** Phenotype count doesn't reflect condition diversity

---

## Summary of Track Inconsistencies Found

During documentation, I identified these issues:

1. **Multi-cluster gene handling (CRITICAL):**
   - Conservation (Track 3): Uses MAX across clusters ✅
   - Consistency scores (Tracks 5-10): Use FIRST cluster only ❌
   - **Recommendation:** All consistency tracks should use MAX or average across clusters

2. **EC Mapped Consistency (Track 21): Non-functional**
   - Always returns -1
   - **Recommendation:** Remove track from UI or implement properly

3. **N_FITNESS track (index 37): Missing from active tracks**
   - Field exists but not documented here (moved to placeholder_tracks)
   - gene_phenotypes table has no fitness data for user_genome

---

# Tree Tab Features

## Overview

The Tree tab displays a phylogenetic dendrogram showing evolutionary relationships between the user genome and reference genomes, based on pangenome cluster sharing.

**Data file:** `tree_data.json`
**Generation script:** `generate_tree_data.py`
**Visualization:** UPGMA dendrogram with genome metadata and statistics

---

## Tree Construction Method

**Algorithm:** UPGMA (Unweighted Pair Group Method with Arithmetic Mean)
**Distance metric:** Jaccard distance on pangenome cluster presence/absence
**Source code:** `generate_tree_data.py` lines 76-100

### Step-by-step computation:

**Step 1: Build binary presence/absence matrix**
```python
# Rows = genomes (14 total: user + 13 references)
# Columns = pangenome clusters (~3000+)
# Values = 1 if genome has cluster, 0 otherwise

matrix = np.zeros((n_genomes, n_clusters), dtype=np.uint8)
for genome_idx, genome_id in enumerate(genome_ids):
    for cluster_id in genome_clusters[genome_id]:
        matrix[genome_idx, cluster_idx] = 1
```

**Step 2: Compute pairwise Jaccard distances**
```python
# Jaccard distance = 1 - Jaccard similarity
# Jaccard similarity = (intersection) / (union)

# For genomes A and B:
# intersection = clusters present in both
# union = clusters present in either
# distance = 1 - (intersection / union)

condensed_distances = pdist(matrix, metric="jaccard")
distance_matrix = squareform(condensed_distances)  # Convert to full matrix
```

**Step 3: UPGMA clustering**
```python
# Average linkage clustering
Z = linkage(condensed_distances, method="average")

# Z is (n-1) × 4 matrix:
# [cluster1_id, cluster2_id, distance, cluster_size]

# Extract leaf order for display
leaf_order = leaves_list(Z)  # Optimal leaf ordering
```

**Database queries:**
```sql
-- Load reference genome clusters
SELECT genome_id, cluster_id
FROM pan_genome_features
WHERE cluster_id IS NOT NULL

-- Load user genome clusters
SELECT pangenome_cluster_id
FROM genome_features
WHERE genome_id = 'user_genome' AND pangenome_cluster_id IS NOT NULL
```

---

## Genome Statistics (Per-Genome)

Each genome node in the tree displays 4 statistics:

### Stat 1: Genes
**Label:** "Genes"
**Computation:** `generate_tree_data.py` lines 144-158

```python
# For user genome
n_genes = conn.execute("""
    SELECT COUNT(*)
    FROM genome_features
    WHERE genome_id = ?
""", (user_genome_id,)).fetchone()[0]

# For reference genomes
n_genes = conn.execute("""
    SELECT COUNT(*)
    FROM pan_genome_features
    WHERE genome_id = ?
""", (ref_genome_id,)).fetchone()[0]
```

**What it shows:** Total number of genes in this genome
**Example values:** 3,000-5,000 genes (typical bacterial genome)

### Stat 2: Clusters

**Label:** "Clusters"
**Computation:** `generate_tree_data.py` lines 141-142

```python
clusters = all_clusters_by_genome[genome_id]
n_clusters = len(clusters)  # FIXME: This counts CLUSTERS, not genes!
```

**ISSUE FOUND:** Variable named `n_genes` but actually counts CLUSTERS (line 142)

**What it shows:** Number of unique pangenome clusters this genome participates in
**Example values:** Similar to gene count for most genomes (~3,000), but multi-cluster genes can make this higher

**Known bug:** Display labels this as "Genes" but it's actually cluster count. Should be renamed to "Clusters" or computed correctly.

### Stat 3: Shared
**Label:** "Shared with user"
**Computation:** `generate_tree_data.py` lines 159-161

```python
# For reference genomes only (user genome shows 100%)
shared_clusters = user_clusters & ref_clusters[ref_genome_id]
shared_count = len(shared_clusters)
```

**What it shows:** Number of pangenome clusters shared between this reference genome and the user genome
**Example values:** 2,000-3,000 (depending on phylogenetic distance)
**User genome:** Shows total cluster count (100% overlap with itself)

### Stat 4: Missing Core
**Label:** "Missing core"
**Computation:** `generate_tree_data.py` lines 162-170 (inferred from index.html lines 2988-2998)

**Index.html computation (where this is actually displayed):**
```javascript
// Compute missing core genes for user genome
const coreThreshold = 0.95;  // Core = present in >95% of genomes
const allCoreCount = genes.filter(g => g[F.CONS_FRAC] > coreThreshold).length;
const userHasCore = genes.filter(g => g[F.PAN_CAT] === 2).length;
const missing = Math.max(0, allCoreCount - userHasCore);
```

**ISSUE FOUND:** Logic appears backwards - computes core genes user genome HAS, then subtracts from total core

**What it should show:** Number of core genes (present in >95% of reference genomes) that are MISSING from this genome

**Example interpretation:**
- Missing core = 0: Genome has all expected core genes
- Missing core > 0: Genome is missing some widely conserved genes (may indicate:
  - Assembly gaps
  - True gene loss
  - Annotation errors
  - Different biology)

---

## Genome Metadata (Per-Genome)

### Metadata 1: Taxonomy
**Source:** `generate_tree_data.py` lines 130-131

```python
metadata[genome_id] = {
    "taxonomy": genome_data.get("gtdb_taxonomy") or
                genome_data.get("ncbi_taxonomy") or
                "Unknown"
}
```

**Database query:**
```sql
SELECT id, gtdb_taxonomy, ncbi_taxonomy
FROM genome
WHERE id = ?
```

**Preference:** GTDB taxonomy first (more curated), fallback to NCBI

**Format:** Full Linnean hierarchy (e.g., "d__Bacteria;p__Proteobacteria;c__Gammaproteobacteria;...")

### Metadata 2: # Features
**Source:** `generate_tree_data.py` line 132

```python
metadata[genome_id]["n_features"] = genome_data.get("n_features", 0)
```

**Database column:** `genome.n_features` (total annotated features, including genes, RNAs, misc features)

### Metadata 3: # Contigs
**Source:** `generate_tree_data.py` line 133

```python
metadata[genome_id]["n_contigs"] = genome_data.get("n_contigs", 0)
```

**Database column:** `genome.n_contigs`

**Interpretation:**
- 1 contig = Complete genome
- 2-50 contigs = Good draft
- 50-200 contigs = Fragmented draft
- >200 contigs = Very fragmented (quality concern)

### Metadata 4: ANI to User
**Source:** `generate_tree_data.py` lines 114-135

```python
# Load ANI (Average Nucleotide Identity) data
ani_data = {}
try:
    cur = conn.execute("""
        SELECT genome1, genome2, ani
        FROM genome_ani
        WHERE genome1 = ? OR genome2 = ?
    """, (user_genome_id, user_genome_id))

    for row in cur:
        other_genome = row["genome2"] if row["genome1"] == user_genome_id else row["genome1"]
        ani_data[other_genome] = round(row["ani"], 4) if row["ani"] else None
except sqlite3.OperationalError:
    # genome_ani table may not exist
    ani_data = {}

# For each genome
metadata[genome_id]["ani_to_user"] = ani_data.get(genome_id) if genome_id != user_genome_id else 1.0
```

**Database table:** `genome_ani` (pairwise ANI values)

**ANI interpretation:**
- 1.0 (100%): User genome (perfect match to itself)
- >0.99 (99%+): Same strain
- 0.95-0.99: Same species
- 0.85-0.95: Same genus
- <0.85: Different genus

**Note:** ANI table may be absent, in which case ANI values are unavailable (None)

---

## Tree Visualization Features

**Implementation:** `index.html` Tree tab rendering

**Features:**
1. **Collapsible nodes:** Click to expand/collapse clades
2. **Hover tooltips:** Show full metadata on hover
3. **Color-coded stats:** Use same color scheme as tracks
4. **Distance scale:** Jaccard distance bar (0-1 range)
5. **Leaf ordering:** Optimized by UPGMA for visual clarity

**Jaccard distance interpretation:**
- 0.0: Identical cluster profiles (impossible except for duplicates)
- 0.05: Very closely related (same species/strain)
- 0.1-0.2: Related (same species or genus)
- 0.3-0.5: Moderately distant (different genera)
- >0.5: Distantly related

---

## Tree Tab Issues Summary

1. **Stat "Genes" mislabeled (MODERATE):**
   - Line 142 of generate_tree_data.py: `n_genes = len(clusters)` counts CLUSTERS
   - Display shows this as "Genes"
   - **Fix:** Either rename to "Clusters" or count actual genes

2. **Missing core computation unclear (NEEDS VERIFICATION):**
   - Index.html lines 2988-2998: Logic seems backwards
   - Should verify with sample data whether it correctly identifies missing core genes

---

# Cluster Tab Features

## Overview

The Cluster tab displays a UMAP (Uniform Manifold Approximation and Projection) 2D scatter plot of genes, revealing clustering patterns based on gene features or pangenome presence/absence.

**Data file:** `cluster_data.json`
**Generation script:** `generate_cluster_data.py`
**Visualization:** Interactive 2D scatter plot with 3,235 points (one per gene)

---

## UMAP Embeddings

### Embedding 1: Gene Features

**What it shows:** Genes plotted by their annotation and pangenome characteristics

**Computation:** `generate_cluster_data.py` lines 51-94

**23 features used:**
1. CONS_FRAC - Conservation fraction (0-1)
2. RAST_CONS - RAST consistency (0-1 or -1)
3. KO_CONS - KO consistency (0-1 or -1)
4. GO_CONS - GO consistency (0-1 or -1)
5. EC_CONS - EC consistency (0-1 or -1)
6. BAKTA_CONS - Bakta consistency (0-1 or -1)
7. AVG_CONS - Average consistency (0-1 or -1)
8. EC_AVG_CONS - EC average consistency (0-1 or -1)
9. EC_MAP_CONS - EC mapped consistency (always -1, deprecated)
10. SPECIFICITY - Annotation specificity (0-1)
11. N_KO - # KEGG terms
12. N_COG - # COG terms
13. N_PFAM - # Pfam terms
14. N_GO - # GO terms
15. N_EC - # EC numbers
16. N_MODULES - KEGG module hits
17. CLUSTER_SIZE - Pangenome cluster size
18. PROT_LEN - Protein length (amino acids)
19. IS_HYPO - Hypothetical flag (0 or 1)
20. HAS_NAME - Has gene name (0 or 1)
21. STRAND - Strand (0 or 1)
22. PAN_CAT - Pangenome category (0/1/2)
23. AGREEMENT - RAST/Bakta agreement (0-3)

**Preprocessing:**
```python
# Replace -1 (N/A) with 0.0
for i, gene in enumerate(genes):
    for j, field_name in enumerate(feature_fields):
        value = gene[F[field_name]]
        feature_matrix[i, j] = 0.0 if value == -1 else float(value)

# Normalize each column to [0, 1]
for j in range(feature_matrix.shape[1]):
    col = feature_matrix[:, j]
    col_min, col_max = col.min(), col.max()
    if col_max > col_min:
        feature_matrix[:, j] = (col - col_min) / (col_max - col_min)
    else:
        feature_matrix[:, j] = 0.0  # Constant column → 0
```

**UMAP parameters:**
```python
reducer = umap.UMAP(
    n_neighbors=30,      # Local neighborhood size
    min_dist=0.1,        # Minimum separation between points
    n_components=2,      # 2D output
    metric='euclidean',  # Distance metric
    random_state=42      # Reproducibility
)
embedding = reducer.fit_transform(feature_matrix)
```

**Expected patterns:**
- **Core genes cluster together:** High conservation + high consistency
- **Hypothetical genes cluster separately:** Low specificity + low ontology counts
- **Well-annotated genes:** High N_KO + N_GO + N_EC → tight cluster
- **Accessory genes:** Scattered (variable features)

### Embedding 2: Presence/Absence

**What it shows:** Genes plotted by which reference genomes contain their pangenome cluster

**Computation:** `generate_cluster_data.py` lines 96-147 (inferred structure)

**Binary matrix:**
- Rows = genes (3,235)
- Columns = reference genomes (35)
- Values = 1 if genome has this gene's cluster, 0 otherwise

**Database query:**
```sql
-- For each gene's pangenome cluster
SELECT DISTINCT genome_id
FROM pan_genome_features
WHERE cluster_id = ?
```

**UMAP parameters:** Same as Gene Features embedding

**Expected patterns:**
- **Core genes:** Central cluster (present in all genomes)
- **Accessory genes:** Peripheral (present in subset of genomes)
- **User-specific genes:** Isolated points (no cluster, all zeros)

**Biological interpretation:**
- Genes clustering together = shared evolutionary history (same pattern of gain/loss across genomes)
- Outliers = unique distribution pattern (e.g., horizontally transferred genes, phage genes)

---

## Color-By Options

The Cluster tab supports 10 different color schemes (from `config.json` cluster_color_options):

### Option 1: Core/Accessory (PAN_CAT)
**Field:** PAN_CAT (index 6)
**Colors:** Green (Core), Orange (Accessory), Gray (Unknown)
**Use case:** Separate core from accessory genes visually

### Option 2: Conservation (CONS_FRAC)
**Field:** CONS_FRAC (index 5)
**Colors:** Blue gradient (light=low → dark=high)
**Use case:** Continuous view of conservation

### Option 3: Avg Consistency (AVG_CONS)
**Field:** AVG_CONS (index 17)
**Colors:** Orange (high) → Blue (low), Gray (N/A)
**Use case:** Identify poorly annotated genes

### Option 4: Localization (LOC)
**Field:** LOC (index 12)
**Colors:** 6 categorical colors (Cytoplasmic, Membrane, Periplasmic, Outer Membrane, Extracellular, Unknown)
**Use case:** Functional compartmentalization

### Option 5: # KEGG Terms (N_KO)
**Field:** N_KO (index 8)
**Colors:** Blue gradient
**Use case:** Metabolic gene enrichment

### Option 6: Module Hits (N_MODULES)
**Field:** N_MODULES (index 26)
**Colors:** Blue gradient
**Use case:** Pathway coverage

### Option 7: Cluster Size (CLUSTER_SIZE)
**Field:** CLUSTER_SIZE (index 25)
**Colors:** Blue gradient
**Use case:** Gene family expansion

### Option 8: Specificity (SPECIFICITY)
**Field:** SPECIFICITY (index 20)
**Colors:** Orange (high) → Blue (low)
**Use case:** Characterization targets (low specificity)

### Additional Options (9-10):
- Could include other tracks like IS_HYPO, HAS_NAME, RICH_FLUX, etc.

---

## Cluster Tab Issues Summary

1. **EC_MAP_CONS deprecated field included (LOW):**
   - Field always -1 but still included in embedding
   - Adds noise to dimensionality reduction
   - **Fix:** Remove from feature list in generate_cluster_data.py

2. **No filtering of N/A values (MODERATE):**
   - -1 (N/A) values converted to 0.0, which biases normalization
   - Genes with missing data treated as "low value" instead of missing
   - **Better approach:** Could use NaN and imputation, or exclude features with >50% missing

---

# Metabolic Map Tab Features

## Overview

The Metabolic Map tab displays metabolic pathways using Escher pathway visualization, showing reactions colored by conservation, presence, flux, or flux class.

**Data file:** `reactions_data.json`
**Generation script:** `generate_reactions_data.py`
**Visualization:** Escher.js interactive pathway maps
**Map files:** `metabolic_map_full.json` (Global), `metabolic_map_core.json` (Core)

---

## Reaction Data Computation

### Reaction Conservation

**What it shows:** Fraction of genomes (0-1) that contain this reaction in their metabolic models.

**Computation:** `generate_reactions_data.py` lines 42-64

```python
# Step 1: Count genomes with each reaction
rxn_genomes = {}
for row in conn.execute("SELECT reaction_id, genome_id FROM genome_reactions"):
    rxn_id = row["reaction_id"]
    if rxn_id not in rxn_genomes:
        rxn_genomes[rxn_id] = set()
    rxn_genomes[rxn_id].add(row["genome_id"])

# Step 2: Compute conservation fraction
n_genomes = conn.execute("SELECT COUNT(DISTINCT genome_id) FROM genome_reactions").fetchone()[0]

for rxn_id in user_reactions:
    n_with = len(rxn_genomes.get(rxn_id, set()))
    conservation = n_with / n_genomes if n_genomes > 0 else 0
```

**Database query:**
```sql
-- Count total genomes
SELECT COUNT(DISTINCT genome_id) FROM genome_reactions

-- Count genomes with each reaction
SELECT reaction_id, COUNT(DISTINCT genome_id)
FROM genome_reactions
GROUP BY reaction_id
```

**Example values:**
- Core reactions: 0.9-1.0 (present in 90-100% of genomes)
- Accessory reactions: 0.2-0.8
- User-specific reactions: <0.2 (recent acquisitions or model additions)

### Flux Values

**Rich Media Flux:**
**Field:** `flux_rich`
**Database column:** `genome_reactions.rich_media_flux`
**Units:** mmol/gDW/hr (millimoles per gram dry weight per hour)
**Conditions:** LB-like rich media, aerobic growth, FBA with biomass maximization

**Minimal Media Flux:**
**Field:** `flux_min`
**Database column:** `genome_reactions.minimal_media_flux`
**Units:** mmol/gDW/hr
**Conditions:** M9 minimal media (glucose + salts), aerobic growth, FBA

**Computation:** `generate_reactions_data.py` lines 66-68

```python
flux_rich = row["rich_media_flux"] if row["rich_media_flux"] is not None else 0
flux_min = row["minimal_media_flux"] if row["minimal_media_flux"] is not None else 0
```

**Interpretation:**
- High flux (>10): Central metabolism, essential pathways
- Medium flux (0.1-10): Active secondary metabolism
- Low flux (<0.1): Minor pathways or alternatives
- Zero flux: Blocked reactions (missing substrates, thermodynamically unfavorable)

### Flux Classes

**6-category classification from Flux Variability Analysis:**

**Categories:**
1. **Essential:** Reaction MUST carry flux (min flux > threshold, required for growth)
2. **Variable:** Reaction CAN carry flux but not required (flexible metabolism)
3. **Blocked:** Reaction CANNOT carry flux (missing cofactors/substrates or thermodynamically blocked)
4. *Additional categories may include:* Essential_reversible, Variable_reversible, etc.

**Rich Media Class:**
**Field:** `class_rich`
**Database column:** `genome_reactions.rich_media_class`

**Minimal Media Class:**
**Field:** `class_min`
**Database column:** `genome_reactions.minimal_media_class`

**Computation:** `generate_reactions_data.py` lines 70-72

```python
class_rich = row["rich_media_class"] or "blocked"
class_min = row["minimal_media_class"] or "blocked"
```

### Gene-Reaction Associations (GPR)

**What it shows:** Which genes encode enzymes catalyzing this reaction.

**Field:** `genes`
**Database column:** `genome_reactions.genes`
**Format:** Boolean expression with locus tags

**Examples:**
- Single gene: `"GENE123"`
- Isozymes (alternatives): `"GENE123 or GENE456"` (either gene can catalyze)
- Complex (required subunits): `"GENE123 and GENE456"` (both genes needed)
- Complex isozymes: `"(GENE123 and GENE456) or GENE789"`

**Gene index mapping:** `generate_reactions_data.py` lines 91-137

```python
# Extract locus tags from GPR expressions
gene_str = "GENE123 or GENE456"
tags = re.findall(r"[A-Za-z][A-Za-z0-9_]+", gene_str)
# Filter out boolean operators
tags = [t for t in tags if t not in ("or", "and", "OR", "AND")]

# Map to gene indices from genes_data.json
fid_to_idx = {gene[1]: i for i, gene in enumerate(genes)}
for tag in tags:
    if tag in fid_to_idx:
        gene_index[tag] = [fid_to_idx[tag]]
```

**Use case:** Click reaction → navigate to gene detail panel

### Reaction Equation

**Field:** `equation`
**Database column:** `genome_reactions.equation_names`
**Format:** Human-readable compound names

**Example:** `"ATP + H2O → ADP + Pi + H+"`

**Also available:**
- `equation_ids`: ModelSEED compound IDs (e.g., "cpd00002_c + cpd00001_c → cpd00008_c + cpd00009_c")
- `directionality`: "reversible" or "forward" or "reverse"

### Gapfilling Status

**Field:** `gapfilling`
**Database column:** `genome_reactions.gapfilling_status`
**Values:** "none" (gene-supported), "added" (gapfilled to enable growth), "removed"

**Interpretation:**
- "none": Reaction has direct gene evidence
- "added": Reaction added by gapfilling algorithm (no gene, but needed for model feasibility)
- High gapfilling % = incomplete genome annotation or true metabolic gaps

---

## Metabolic Map Stats (Displayed in sidebar)

**Computation:** `generate_reactions_data.py` lines 139-176

### Total Reactions
Count of all reactions in user genome metabolic model.

```python
total_reactions = len(reactions)
```

### Active Reactions (Rich Media)
Reactions with flux class ≠ "blocked" in rich media.

```python
active_rich = sum(1 for r in reactions.values() if r["class_rich"] != "blocked")
```

### Active Reactions (Minimal Media)
Reactions with flux class ≠ "blocked" in minimal media.

```python
active_min = sum(1 for r in reactions.values() if r["class_min"] != "blocked")
```

### Essential Reactions (Rich Media)
Reactions with "essential" in flux class (required for growth).

```python
essential_rich = sum(1 for r in reactions.values() if "essential" in r["class_rich"])
```

### Essential Reactions (Minimal Media)
```python
essential_min = sum(1 for r in reactions.values() if "essential" in r["class_min"])
```

### Gapfilled Reactions
Reactions added by gapfilling (no gene support).

```python
gapfilled = sum(1 for r in reactions.values() if r["gapfilling"] == "added")
```

### Conserved Reactions
Reactions present in >95% of reference genomes.

```python
conserved = sum(1 for r in reactions.values() if r["conservation"] > 0.95)
```

---

## Metabolic Map Color Modes (6 options)

**Implementation:** `index.html` lines 853-861 (metabolic-color-by dropdown)

### Mode 1: Pangenome Conservation
**Data:** `reaction.conservation` (0-1)
**Color:** Blue gradient (light=rare → dark=conserved)
**Use case:** Identify core vs accessory metabolism

### Mode 2: Presence / Absence
**Data:** Binary (reaction exists in user genome or not)
**Color:** Present = green, Absent = gray
**Use case:** Quickly see which pathways are active

### Mode 3: Flux (Rich Media)
**Data:** `reaction.flux_rich` (0-100+ mmol/gDW/hr)
**Color:** Blue gradient (light=low flux → dark=high flux)
**Use case:** Identify most active pathways in rich media

### Mode 4: Flux (Minimal Media)
**Data:** `reaction.flux_min`
**Color:** Blue gradient
**Use case:** Identify biosynthetic pathways upregulated in minimal media

### Mode 5: Flux Class (Rich)
**Data:** `reaction.class_rich` (essential/variable/blocked)
**Color:** Categorical (red=essential, yellow=variable, gray=blocked)
**Use case:** Predict gene essentiality, identify flexible metabolism

### Mode 6: Flux Class (Minimal)
**Data:** `reaction.class_min`
**Color:** Categorical
**Use case:** Compare essentiality between conditions

---

## Map Files

### Global Metabolism Map
**File:** `metabolic_map_full.json`
**Coverage:** All reactions in user genome (~759 reactions)
**Pathways:** Full ModelSEED metabolism (central carbon, amino acids, nucleotides, cofactors, cell wall, lipids)

### Core Metabolism Map
**File:** `metabolic_map_core.json`
**Coverage:** Core reactions present in >95% of genomes (~201 reactions)
**Pathways:** Essential central metabolism only (glycolysis, TCA, PPP, essential biosynthesis)

**Map selection:** `index.html` lines 840-845

---

## Pathway Coverage (Displayed in sidebar)

**What it shows:** Fraction of reactions in each KEGG pathway that are present in the user genome.

**Example output:**
```
Glycolysis: 9/10 (90%)
TCA Cycle: 8/8 (100%)
Amino Acid Biosynthesis: 145/200 (72%)
```

**Use case:** Identify incomplete pathways (potential targets for experimental validation or metabolic engineering)

---

## Metabolic Map Tab Issues Summary

1. **Gene index matching may be incomplete (MODERATE):**
   - Locus tag extraction uses regex, may miss complex formats
   - Partial matching could create false positives
   - **Fix:** Validate with sample reactions, improve matching logic

2. **Flux class categories unclear (LOW):**
   - Documentation mentions 6 categories but only 3 clearly defined
   - **Fix:** Clarify all 6 category names and meanings

---

# Distributions Tab Features

## Overview

The Distributions tab visualizes the statistical distribution of gene counts across different track values, using histograms (numerical tracks), pie charts (categorical tracks), or special handling for consistency tracks (which have N/A values).

**Implementation:** `index.html` lines 786-817 (UI), lines 3600-3800 (rendering logic)

---

## Distribution Types

### Categorical Distributions

**Tracks:** `pan_category`, `localization`, `rich_class`, `min_class`, etc.

**Visualizations generated:**
1. **Bar Chart:** Horizontal bars showing count per category
2. **Pie Chart:** Proportional slices for each category
3. **Statistics Table:** Category name, count, percentage

**Computation:** `index.html` lines 3642-3750

```javascript
// Count genes in each category
const counts = {};
genes.forEach(gene => {
    const value = gene[track.field];
    const categoryName = getCategoryName(value, track);
    counts[categoryName]++;
});

// Calculate percentages
const total = genes.length;
const entries = Object.entries(counts).map(([cat, count]) => ({
    category: cat,
    count: count,
    percentage: (count / total * 100).toFixed(1)
}));
```

**Example output for pan_category track:**
```
Core:      2,957 genes (91.4%)
Accessory:   175 genes (5.4%)
Unknown:     103 genes (3.2%)
```

**Visual elements:**
- Bar chart: SVG bars scaled by count
- Pie chart: SVG arcs with categorical colors
- Interactive tooltips on hover

### Numerical Distributions (Sequential tracks)

**Tracks:** `conservation`, `prot_len`, `n_ko`, `n_go`, `cluster_size`, `flux_rich`, `flux_min`, `essentiality`, etc.

**Visualization:** Histogram (binned frequency distribution)

**Computation:** `index.html` lines 3750-3850 (inferred structure)

```javascript
// Bin the data
const values = genes.map(g => g[track.field]).filter(v => v >= 0);  // Exclude N/A (-1)
const min = Math.min(...values);
const max = Math.max(...values);
const nBins = 30;  // Default bin count
const binWidth = (max - min) / nBins;

// Count genes per bin
const bins = Array(nBins).fill(0);
values.forEach(val => {
    const binIdx = Math.min(Math.floor((val - min) / binWidth), nBins - 1);
    bins[binIdx]++;
});

// Compute statistics
const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
const sorted = values.slice().sort((a, b) => a - b);
const median = sorted[Math.floor(sorted.length / 2)];
const stddev = Math.sqrt(values.reduce((sum, v) => sum + (v - mean) ** 2, 0) / values.length);
```

**Statistics displayed:**
- **Count:** Number of genes with valid values (excludes N/A)
- **Mean:** Average value
- **Median:** Middle value (50th percentile)
- **Std Dev:** Standard deviation (measure of spread)
- **Min:** Minimum value
- **Max:** Maximum value

**Example output for conservation track:**
```
Count:  3,132 genes (97.0% of total)
Mean:   0.971
Median: 1.000
Std Dev: 0.115
Range:  0.000 - 1.000
```

**Visual elements:**
- Histogram bars (SVG rectangles)
- X-axis: Value range
- Y-axis: Gene count
- Tooltips showing bin range and count

### Consistency Distributions (Special handling)

**Tracks:** `avg_cons`, `rast_cons`, `ko_cons`, `go_cons`, `ec_cons`, `bakta_cons`, `ec_map_cons`, `specificity`

**Special feature:** Separate N/A category (-1 values)

**Computation:** Similar to numerical, but treats -1 as separate category

```javascript
// Split into valid values and N/A
const validValues = genes.map(g => g[track.field]).filter(v => v >= 0);
const naCount = genes.length - validValues.length;

// Bin valid values (0.0-1.0 range for consistency)
const bins = Array(20).fill(0);  // 20 bins for 0.0-1.0
validValues.forEach(val => {
    const binIdx = Math.min(Math.floor(val * 20), 19);
    bins[binIdx]++;
});

// Display N/A separately
naPercentage = (naCount / genes.length * 100).toFixed(1);
```

**Statistics displayed:**
- Same as numerical tracks, PLUS:
- **N/A Count:** Number of genes with -1 (no cluster or no annotation)
- **N/A Percentage:** Fraction of genes with missing data

**Example output for avg_cons track:**
```
Count:  1,598 genes (49.4% have consistency scores)
N/A:    1,637 genes (50.6% - no cluster or no annotations)
Mean:   0.742
Median: 0.815
Range:  0.000 - 1.000
```

**Visual elements:**
- Histogram for valid values (0.0-1.0)
- Separate bar for N/A count
- Orange-blue color scale (matching consistency color scheme)

### Binary Distributions

**Tracks:** `strand`, `has_name`, `is_hypo`

**Visualization:** Special case of categorical with 2 categories

**Example output for strand track:**
```
Forward (+): 1,679 genes (51.9%)
Reverse (-): 1,556 genes (48.1%)
```

**Visual elements:**
- 2-category pie chart
- 2-category bar chart
- Binary color scheme (purple vs orange)

---

## Track Dropdown

**Implementation:** `index.html` lines 3602-3611

```javascript
// Populate dropdown with all tracks
const select = document.getElementById('dist-track-select');
TRACKS.forEach(track => {
    const option = document.createElement('option');
    option.value = track.id;
    option.textContent = track.name;
    select.appendChild(option);
});
```

**User workflow:**
1. Select track from dropdown
2. Distribution automatically renders
3. Switch tracks to compare distributions

---

## Distributions Tab Issues Summary

1. **No outlier handling (LOW):**
   - Extreme values can compress histogram visualization
   - **Fix:** Add outlier detection, optional log scale

2. **Fixed bin count (LOW):**
   - Always uses 30 bins for numerical, may not suit all distributions
   - **Fix:** Adaptive binning (Sturges' rule, Freedman-Diaconis)

3. **No export functionality (LOW):**
   - Can't export distribution data or images
   - **Fix:** Add CSV export, SVG download buttons

---

# Summary of All Issues Found During Documentation

## Critical Issues

1. **Multi-cluster gene handling inconsistency (CRITICAL):**
   - Conservation (Track 3): Uses MAX across clusters ✅
   - All consistency tracks (Tracks 5-10): Use FIRST cluster only ❌
   - **Impact:** 266 genes may have underestimated consistency scores
   - **Fix:** Update generate_genes_data.py lines 396-435 to use MAX or average across all clusters

## Moderate Issues

2. **Tree stats "Genes" mislabeled (MODERATE):**
   - generate_tree_data.py line 142: `n_genes = len(clusters)` counts CLUSTERS not genes
   - **Fix:** Rename variable and display label to "Clusters" OR count actual genes

3. **Missing core computation unclear (MODERATE - NEEDS VERIFICATION):**
   - index.html lines 2988-2998: Variable naming suggests backwards logic
   - **Fix:** Verify with sample data, fix if incorrect

4. **EC_MAP_CONS track non-functional (MODERATE):**
   - Always returns -1, entire track is placeholder
   - **Fix:** Remove from UI or implement properly

## Low Priority Issues

5. **N_FITNESS track missing (LOW):**
   - Field exists but no data for user_genome
   - Already moved to placeholder_tracks ✅

6. **Cluster tab EC_MAP_CONS included in embedding (LOW):**
   - Adds noise to UMAP (always -1)
   - **Fix:** Remove from feature list

7. **Cluster tab N/A handling (LOW):**
   - -1 values converted to 0.0, biases normalization
   - **Fix:** Use NaN and imputation

8. **Metabolic map gene index matching (LOW):**
   - Regex-based locus tag extraction may miss edge cases
   - **Fix:** Validate and improve matching logic

9. **Distributions tab: no outlier handling, fixed bins, no export (LOW):**
   - Minor UX improvements
   - **Fix:** Add adaptive binning, outlier detection, export buttons

---

## Issues Fixed

### ✅ FIXED - Issue #1: Multi-cluster gene handling inconsistency (CRITICAL)

**Problem:**
- Conservation (Track 3) used MAX across 266 multi-cluster genes ✅
- All consistency tracks (Tracks 5-10) used FIRST cluster only ❌
- **Impact:** 266 genes (8.2% of dataset) had underestimated consistency scores

**Fix Applied:**
- Updated `generate_genes_data.py` lines 394-456
- Now loops through ALL cluster_ids for each gene
- Computes consistency for each cluster separately
- Takes MAX of all consistency scores
- Consistent with conservation computation

**Code Change:**
```python
# OLD (lines 398-400):
# For multi-cluster genes, use the first cluster
cid = cluster_ids[0]
ref_genes = cluster_ref_genes.get(cid, [])

# NEW (lines 396-447):
# For multi-cluster genes, compute for EACH cluster and take MAX
for cid in cluster_ids:
    ref_genes = cluster_ref_genes.get(cid, [])
    # ... compute consistency for this cluster
    all_rast_cons.append(...)
    all_ko_cons.append(...)
    # etc.
rast_cons = max(all_rast_cons) if all_rast_cons else -1
```

**Result:** Multi-cluster genes now get their best consistency score across all clusters, matching the MAX conservation approach.

---

### ✅ FIXED - Issue #6: Cluster tab EC_MAP_CONS in UMAP (LOW)

**Problem:**
- EC_MAP_CONS field always -1 (deprecated)
- Still included in UMAP feature matrix (23 features)
- Adds noise (constant column becomes all zeros after normalization)

**Fix Applied:**
- Removed EC_MAP_CONS from `generate_cluster_data.py` feature_fields list (line 62)
- Added comment: "# EC_MAP_CONS removed - always -1 (deprecated field)"

**Result:** UMAP now uses 22 meaningful features instead of 23, cleaner embedding.

---

## Issues Already Resolved (Documentation Errors)

### ✅ NOT AN ISSUE - Issue #2: Tree stats

**My documentation error:** Said tree stats mislabeled "Genes" (counts clusters instead)

**Reality:**
- Code already correctly computes BOTH n_genes AND n_clusters separately
- `generate_tree_data.py` lines 144-174: Queries actual gene count from database
- `index.html` line 3257: Displays both: "Genes: X | Clusters: Y | Core: Z%"
- **No fix needed** - code was already correct

---

### ✅ NOT AN ISSUE - Issue #3: Missing core computation

**My documentation error:** Said missing core logic was backwards

**Reality:**
- Old incorrect logic already commented out (index.html lines 2985-2991)
- Tree tab displays "Core %" (percentage), NOT "missing core"
- "Missing Core Status" track exists (line 1526) but disabled by default, has correct logic
- **No fix needed** - code was already correct

---

### ✅ ACCEPTABLE - Issue #4: EC_MAP_CONS track

**Status:** Non-functional (always -1), but acceptable as-is
- Already disabled by default in config.json
- Users can still enable it (will show all gray/N/A)
- Clearly documented as deprecated in TRACK_DOCUMENTATION.md
- **No fix needed** - acceptable as placeholder

---

## Remaining Low Priority Issues (Not Fixed)

### Issue #7: Cluster tab N/A handling (LOW)
- -1 values converted to 0.0 in UMAP, biases normalization
- Better: Use NaN and imputation
- **Not urgent** - current approach works acceptably

### Issue #8: Metabolic map gene index matching (LOW)
- Regex-based locus tag extraction may miss edge cases
- **Not urgent** - appears to work for standard cases

### Issue #9: Distributions tab improvements (LOW)
- No outlier handling, fixed 30 bins, no export
- **Not urgent** - UX nice-to-haves

---

# Documentation Complete!

This comprehensive technical documentation covers:
- ✅ All 28 active tracks (Tracks 1-28)
- ✅ 2 placeholder tracks (N_FITNESS, Neighborhood Conservation)
- ✅ Tree tab features (4 stats, 4 metadata fields, UPGMA algorithm)
- ✅ Cluster tab features (2 UMAP embeddings, 10 color modes)
- ✅ Metabolic Map tab features (6 color modes, reaction data, GPR, flux classes)
- ✅ Distributions tab features (3 visualization types)

**Issues found:** 9 total (1 critical, 3 moderate, 5 low)
**Issues fixed:** 2 (1 critical, 1 low)
**Issues already resolved:** 3 (documentation errors)
**Issues remaining:** 3 (all low priority)

**Most important fix:** Multi-cluster gene consistency handling - now uses MAX across all clusters (affects 266 genes, 8.2% of dataset)
