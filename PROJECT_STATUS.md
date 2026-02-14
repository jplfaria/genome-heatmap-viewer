# Genome Feature Profiler — Project Status

**Live site:** https://jplfaria.github.io/genome-heatmap-viewer/
**Organism:** *Escherichia coli* K-12 MG1655 (GCF_000005845.2)
**Genome ID:** 562.61143
**Last updated:** 2026-02-13

---

## Overview

A multi-view genome visualization tool that profiles gene features across conservation, function consistency, annotation depth, and pangenome structure. Built for KBase/BERDL integration.

- **4,617 genes** with 29 data fields each
- **36 genomes** in pangenome (35 references + user genome)
- Pure vanilla HTML/CSS/JS (2,884 lines), Canvas API + SVG, no frameworks, no build step
- Config-driven via `config.json`
- KBase-branded UI (PR #1 by David Lyon)

---

## 4 Visualization Tabs

| Tab | Rendering | What it shows |
|-----|-----------|---------------|
| **Tracks** | Canvas | Multi-track heatmap of all 4,617 genes across 24 data tracks. Minimap navigation, zoom 1-100x, gene search, hover tooltips |
| **Tree** | SVG | UPGMA dendrogram of 36 genomes (Jaccard distance on pangenome clusters). Collapsible stat bars per genome |
| **Clusters** | Canvas | UMAP 2D scatter of genes in two embedding spaces (gene features / presence-absence), colored by any track |
| **Metabolic Map** | Escher/SVG | Interactive pathway maps (Global 746 rxns, Core 201 rxns). Color by conservation, flux, flux class, or presence. Reaction click shows detail panel |

---

## Data Pipeline

### Source Data

- **Primary:** BERDL SQLite database (`berdl_tables_ontology_terms.db`, 148 MB)
  - Produced by [KBDatalakeApps](https://github.com/kbaseapps/KBDatalakeApps) pipeline
  - Tables: `genome_features`, `pan_genome_features`, `genome`, `genome_ani`, `phenotype_module`, `ontology_terms`
- **Temporary:** `genome_reactions.tsv` — will be added to the SQLite DB in a future pipeline update
- **Static:** ModelSEED Escher pathway maps (organism-agnostic)

### Generation Scripts

| Script | Input | Output | Size | Status |
|--------|-------|--------|------|--------|
| `generate_genes_data.py` | SQLite DB | `genes_data.json` (4,617 genes x 29 fields) | 656 KB | Stable |
| `generate_tree_data.py` | SQLite DB | `tree_data.json` (36 genomes, UPGMA linkage) | 14 KB | Stable |
| `generate_cluster_data.py` | SQLite DB + genes_data.json | `cluster_data.json` (4,617 2D points x 2 modes) | 337 KB | Stable |
| `generate_reactions_data.py` | genome_reactions.tsv | `reactions_data.json` (1,279 reactions) | 383 KB | **TSV source is temporary** |

### Static Map Files

| File | Description | Size |
|------|-------------|------|
| `metabolic_map_full.json` | Global Metabolism Escher map (746 reactions) | 1.8 MB |
| `metabolic_map_core.json` | Core Metabolism Escher map (201 reactions) | 430 KB |

### How to Regenerate

```bash
# Gene data (requires SQLite DB)
python3 generate_genes_data.py [DB_PATH]

# Tree data (requires: numpy, scipy)
python3 generate_tree_data.py

# Cluster data (requires: numpy, umap-learn)
python3 generate_cluster_data.py

# Reaction data (requires genome_reactions.tsv)
python3 generate_reactions_data.py
```

---

## Gene Data Fields (29 per gene)

| Index | Field | Type | Description |
|-------|-------|------|-------------|
| 0 | ID | int | Gene order in genome (feature_id as int) |
| 1 | FID | string | Feature ID (e.g., `562.61143.CDS.1234`) |
| 2 | LENGTH | int | Gene length (bp) |
| 3 | START | int | Genome start position |
| 4 | STRAND | int | 1 = forward, 0 = reverse |
| 5 | CONS_FRAC | float | Fraction of reference genomes with this pangenome cluster (0-1) |
| 6 | PAN_CAT | int | 0 = Unknown, 1 = Accessory, 2 = Core |
| 7 | FUNC | string | Function annotation (RAST preferred, Bakta fallback) |
| 8 | N_KO | int | Number of KEGG Orthology terms |
| 9 | N_COG | int | Number of COG terms |
| 10 | N_PFAM | int | Number of Pfam domains |
| 11 | N_GO | int | Number of GO terms |
| 12 | LOC | int | PSORTb localization (0=Cytoplasmic, 1=CytoMembrane, 2=Periplasmic, 3=OuterMembrane, 4=Extracellular, 5=Unknown) |
| 13 | RAST_CONS | float | RAST consistency (-1=N/A, 0=disagree, 1=agree) |
| 14 | KO_CONS | float | KO consistency |
| 15 | GO_CONS | float | GO consistency |
| 16 | EC_CONS | float | EC consistency |
| 17 | AVG_CONS | float | Average consistency across all sources |
| 18 | BAKTA_CONS | float | Bakta consistency |
| 19 | EC_AVG_CONS | float | EC + EC-mapped average consistency |
| 20 | SPECIFICITY | float | Annotation specificity/precision (0-1, see below) |
| 21 | IS_HYPO | int | 1 if BOTH RAST and Bakta say "hypothetical protein" |
| 22 | HAS_NAME | int | 1 if gene has an official gene name |
| 23 | N_EC | int | Number of EC numbers |
| 24 | AGREEMENT | int | RAST/Bakta agreement (0=Both Hypo, 1=One Hypo, 2=Disagree, 3=Agree) |
| 25 | CLUSTER_SIZE | int | Pangenome cluster size (number of genes) |
| 26 | N_MODULES | int | Number of KEGG modules hit by this gene's KO terms |
| 27 | EC_MAP_CONS | float | EC-mapped consistency (average of ec_mapped_consistency JSON values) |
| 28 | PROT_LEN | int | Protein length (amino acids) |

### Consistency Scores

Each consistency score compares the user genome's annotation for a gene against other genes in the same pangenome cluster:
- **1.0** (green): all genes in cluster agree on annotation
- **0.0** (red): no agreement
- **-1.0** (gray): not applicable (no data or no cluster)

Computed per annotation source (RAST, KO, GO, EC, Bakta) plus an average across all sources.

### Annotation Specificity

Measures how precise/detailed the functional annotation is. Based on ontology evidence and annotation text quality:

| Evidence | Score |
|----------|-------|
| EC number assigned | 0.9 |
| KO term assigned | 0.7 |
| Gene name assigned | 0.6 |
| COG or GO assigned | 0.5 |
| Pfam domain assigned | 0.4 |
| Function text only (no ontology) | 0.3 |
| Bonus: EC cited in function text | +0.1 |

Capped for vague language:
- "putative" / "predicted" / "probable" / "possible" -> cap at 0.5
- "uncharacterized" / "DUF" / "hypothetical [named]" -> cap at 0.3
- "conserved protein of unknown function" -> cap at 0.2
- "hypothetical protein" (generic) -> 0.0

### IS_HYPO Definition

IS_HYPO = 1 only when **both** RAST and Bakta annotate the gene as generic "hypothetical protein". Named hypothetical proteins (e.g., "Hypothetical protein YhiL") are NOT counted as hypothetical.

### Multi-Cluster Genes

266 genes are assigned to 2-4 pangenome clusters (semicolon-separated `pangenome_cluster_id` in the DB). For these genes:
- `pangenome_is_core` is NULL in the DB
- Conservation: take the **maximum** across clusters (per Chris Henry's guidance)
- PAN_CAT: classified as Core if **any** cluster is marked core in `pan_genome_features`

---

## Gene Statistics

| Metric | Count | Percentage |
|--------|-------|------------|
| Total genes | 4,617 | 100% |
| Core genes | 3,626 | 78.5% |
| Accessory genes | 587 | 12.7% |
| Unknown (no cluster) | 404 | 8.8% |
| Hypothetical (both tools) | 102 | 2.2% |
| Named genes | 3,955 | 85.7% |

### RAST/Bakta Agreement

| Category | Count |
|----------|-------|
| Both Hypothetical | 102 |
| One Hypothetical | 262 |
| Disagree (different functions) | 3,925 |
| Agree (same function) | 328 |

### Specificity Distribution

| Range | Label | Count |
|-------|-------|-------|
| 1.0 | Very specific (EC + enzyme) | 1,172 |
| 0.8-0.9 | Specific | 556 |
| 0.6-0.7 | Good (KO or gene name) | 1,572 |
| 0.4-0.5 | Moderate | 192 |
| 0.1-0.3 | Vague (putative, uncharacterized) | 640 |
| 0.0 | Hypothetical protein | 81 |
| -1.0 | N/A (no cluster) | 404 |

### Vague Annotations (not flagged by IS_HYPO)

| Keyword | Count |
|---------|-------|
| uncharacterized | 457 |
| putative | 136 |
| probable | 29 |
| predicted | 23 |
| DUF (domain of unknown function) | 20 |
| possible | 7 |
| conserved protein of unknown function | 4 |

---

## Metabolic Map Data

**Current data source:** `genome_reactions.tsv` (Acinetobacter placeholder)
**Note:** This is temporary. E. coli reaction data will arrive when the table is added to the SQLite DB.

| Metric | Value |
|--------|-------|
| Total reactions | 1,279 |
| Genomes in comparison | 14 |
| Active (rich media) | 759 |
| Active (minimal media) | 696 |
| Blocked (rich) | 520 |
| Blocked (minimal) | 583 |
| Essential (rich) | 248 |
| Essential (minimal) | 225 |

### Escher Map Coverage

| Map | Reactions on map | With user data | Coverage |
|-----|-----------------|----------------|----------|
| Global Metabolism | 746 | 497 | 67% |
| Core Metabolism | 201 | 119 | 59% |

Gene cross-linking between reactions and gene indices will not connect until E. coli reaction data arrives (current data is Acinetobacter, gene IDs don't match).

---

## UI Features

### Tracks Tab
- **24 active data tracks** covering conservation, consistency (6 sources), annotation counts (KO, COG, Pfam, GO, EC), localization, pangenome category, specificity, agreement, cluster size, KEGG module hits, protein length
- **6 placeholder tracks** awaiting data: neighborhood conservation, flux (minimal/rich), rxn class (minimal/rich), # phenotypes, # fitness scores
- **7 sort presets:** genome order, conservation, consistency, annotation depth, pangenome status, lowest consistency, strand blocks
- **6 analysis view presets:** Characterization Targets, Annotation Quality, Metabolic Landscape, Pangenome Structure, Knowledge Coverage, Consistency Comparison
- Genome minimap with draggable viewport
- Gene search with minimap highlight markers
- Zoom slider (1x to 100x)
- Hover tooltips with full gene details and track-specific explanations

### Tree Tab
- UPGMA dendrogram from Jaccard distances on pangenome cluster presence/absence
- Sqrt-scaled branch lengths for visual clarity
- Collapsible stat bars: gene count, cluster count, core % per genome
- Click genome leaf for metadata

### Clusters Tab
- UMAP 2D scatter with two embedding modes (Gene Features / Presence-Absence)
- Color by any track (10 options)
- Hover tooltips with gene details
- Zoom/pan with mouse wheel and drag

### Metabolic Map Tab
- Escher library (lazy-loaded from CDN)
- Two maps: Global Metabolism (746 rxns) and Core Metabolism (201 rxns)
- 6 coloring modes: Conservation, Flux (rich/minimal), Flux Class (rich/minimal), Presence
- Click reaction for detail panel (equation, directionality, flux values, gene links)
- Stats panel showing coverage and active/blocked/essential counts

---

## Testing

**71 Playwright tests** across 9 test suites:

| Suite | Tests | What it validates |
|-------|-------|-------------------|
| Tracks Functionality | 8 | Track toggle, sort, zoom, search, minimap |
| Tracks Data Correctness | 8 | Field counts, gene IDs, value ranges |
| Tree Functionality | 5 | SVG rendering, stat bar toggling, distance scale |
| Tree Data Correctness | 5 | Genome count, distance ranges, stat bar headers |
| Cluster Functionality | 5 | Embedding toggle, color-by, point rendering |
| Cluster Data Correctness | 5 | Point count, coordinate ranges, tooltip content |
| Scientific Correctness | 8 | Core fraction 60-90%, strand balance ~50%, protein lengths 20-3000aa, conservation sort ordering |
| Metabolic Map Functionality | 6 | Escher SVG, map selector, color modes, reaction detail |
| Metabolic Map Data | 5 | Reaction counts, map coverage, legend categories |
| Tab Navigation | 2 | Tab switching, KPI persistence |

```bash
npm install
npx playwright install chromium
npx playwright test
```

---

## Known Issues / Open Items

1. **IS_HYPO too narrow:** Only flags 102 genes (2.2%). 660+ genes with vague annotations (putative, uncharacterized, DUF) are classified as "has function". Could benefit from a multi-level characterization quality track.

2. **Reaction data is Acinetobacter placeholder:** Gene cross-links to Tracks tab won't work until E. coli `genome_reactions.tsv` arrives. Metabolic map coloring works but represents wrong organism.

3. **Placeholder tracks (6):** Awaiting data for neighborhood conservation, flux (minimal/rich), rxn class (minimal/rich), # phenotypes, # fitness scores.

4. **RAST/Bakta disagreement very high:** 3,925 genes (85%) disagree. Expected since they use different annotation pipelines (RAST = SEED/FIG subsystems, Bakta = UniProt/RefSeq), but worth noting for stakeholders.

5. **Multi-cluster genes:** 266 genes assigned to 2-4 pangenome clusters. Using "take the higher conservation" per Chris Henry's guidance. Root cause (biological reality vs pipeline artifact) not yet investigated.

6. **FUNC field prefers RAST even when hypothetical:** If RAST says "hypothetical protein" but Bakta has a real function, the displayed function is still RAST's "hypothetical protein". Could prefer the non-hypothetical annotation.

---

## Stakeholders

| Person | Role |
|--------|------|
| Christopher Henry | Requirements, data pipeline |
| Jose Faria (jplfaria) | Developer |
| David Lyon (dauglyon) | UI/UX (KBase restyle) |
| Adam | End user (paper/presentation) |
| Boris | Reference data deployment |

---

## Git History

```
39ec52e  Add gene extraction script, fix IS_HYPO legend, redesign specificity
8e6a114  Merge pull request #1 from dauglyon/kbase-restyle
7f984ad  Restyle UI to KBase brand and fix UX issues
3ac76c9  Add Metabolic Map tab with Escher pathway visualization
3e59066  Add zoom/pan to cluster scatter plot
20e9335  Add tree/cluster views, minimap nav, config system, and 60 Playwright tests
c8f653a  Add analysis views, 8 new data tracks, fix multi-cluster genes
bea89df  Initial commit: Genome Heatmap Viewer prototype
```
