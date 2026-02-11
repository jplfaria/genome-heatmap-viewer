# Multi-Track Genome/Phenotype Heatmap Viewer - Detailed Requirements

**Document Purpose:** Detailed specification of what Christopher Henry wants Jose to build
**Source:** Transcript from `/home/jplfaria/CDM_jose/ontology_data_utils/heatmap.txt` and whiteboard image `heatmap?.png`
**Date:** February 10, 2026

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [The Core Concept](#2-the-core-concept)
3. [Data Tracks Specification](#3-data-tracks-specification)
4. [UI/UX Requirements](#4-uiux-requirements)
5. [Data Sources & Integration](#5-data-sources--integration)
6. [Two View Modes](#6-two-view-modes)
7. [Current State of Codebase](#7-current-state-of-codebase)
8. [Blockers & Dependencies](#8-blockers--dependencies)
9. [Implementation Phases](#9-implementation-phases)
10. [Technical Architecture](#10-technical-architecture)

---

## 1. Executive Summary

Christopher wants a **web-based interactive heatmap visualization tool** that displays genomic data across multiple "tracks" or "bands". Think of it like a genome browser (similar to IGV or UCSC Genome Browser) but focused on showing computed data tracks as heatmaps rather than sequence alignments.

**Key Quote from Christopher:**
> "It's a heat map. It's a big heat map where we... Like Vibhav's thing. Like it's literally just a giant heat map."

**Purpose:** Generate visualizations for Adam (likely for a paper or presentation)

**Output Format:** HTML report that can be viewed in a browser

---

## 2. The Core Concept

### Visual Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  TRACK CONTROLS (left panel)              │  HEATMAP VISUALIZATION          │
│  ┌─────────────────────────────────┐      │                                  │
│  │ [x] Gene order          [sort]  │      │  Gene1  Gene2  Gene3  Gene4 ... │
│  │ [x] Gene length         [sort]  │      │  ┌────┬────┬────┬────┬────────┐ │
│  │ [x] Gene direction      [sort]  │      │  │████│░░░░│████│████│  ...   │ │ ← Track 1
│  │ [ ] Function class      [sort]  │      │  ├────┼────┼────┼────┼────────┤ │
│  │ [x] Pangenome conserv.  [sort]  │      │  │▓▓▓▓│████│░░░░│▓▓▓▓│  ...   │ │ ← Track 2
│  │ [x] Pangenome fraction  [sort]  │      │  ├────┼────┼────┼────┼────────┤ │
│  │ [ ] Neighborhood score  [sort]  │      │  │░░░░│▓▓▓▓│████│░░░░│  ...   │ │ ← Track 3
│  │ [ ] Flux minimal media  [sort]  │      │  ├────┼────┼────┼────┼────────┤ │
│  │ [ ] Rxn class minimal   [sort]  │      │  │████│████│▓▓▓▓│████│  ...   │ │ ← Track 4
│  │ [ ] Rxn class rich      [sort]  │      │  └────┴────┴────┴────┴────────┘ │
│  │ [ ] # phenotypes        [sort]  │      │                                  │
│  │ [ ] # fitness scores    [sort]  │      │  ┌────────────────────────────┐ │
│  │ [ ] Annotation specif.  [sort]  │      │  │  GENOME SELECTOR (zoom)    │ │
│  │ [x] Consensus score     [sort]  │      │  │  [====|----selected----|==]│ │
│  │                                 │      │  └────────────────────────────┘ │
│  │ [Cluster by selected]           │      │                                  │
│  └─────────────────────────────────┘      │                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Concepts

1. **X-axis:** Genes in the genome (4,000+ for E. coli)
2. **Y-axis:** Data tracks (bands of data)
3. **Each cell:** Color-coded value (heatmap style)
4. **Tracks can be:** Added/removed, sorted by, clustered by

---

## 3. Data Tracks Specification

### Track List (from whiteboard image)

| # | Track Name | Data Type | Value Range | Color Scheme | Source |
|---|------------|-----------|-------------|--------------|--------|
| 1 | **Gene order** | Integer | 1 to N | Sequential | `start` column in genome_features |
| 2 | **Function class** | Category | Subsystem categories | Categorical | DROPPED (mapping issues) |
| 3 | **Gene length** | Integer | 0 to ~10,000 bp | Sequential | `length` or `end - start` |
| 4 | **Gene direction** | Binary | +1 / -1 | Two-color | `strand` column |
| 5 | **Pangenome conservation fraction** | Float | 0.0 to 1.0 | Sequential | Computed: count(cluster_id) / total_genomes |
| 6 | **Pangenome conservation** | Category | core/aux/other | 3-color | `pangenome_is_core` or derived |
| 7 | **Neighborhood conservation score** | Float | 0.0 to 1.0 | Sequential | From BERDL (not yet available) |
| 8 | **Flux in pyruvate minimal media** | Float | -1000 to 1000 | Diverging | FBA results (not yet available) |
| 9 | **Reaction classification minimal media** | Category | blocked/active/essential | 3-color | FVA results (not yet available) |
| 10 | **Reaction classification rich media** | Category | blocked/active/essential | 3-color | FVA results (not yet available) |
| 11 | **Number of phenotypes linked to gene** | Integer | 0 to 150+ | Sequential | Model-gene-phenotype mapping |
| 12 | **Number of fitness scores above threshold** | Integer | 0 to N | Sequential | fitness.py data |
| 13 | **Functional annotation specificity** | Float | 0.0 to 1.0 | Sequential | Computed from RAST annotations |
| 14 | **Function consensus score** | Float | 0.0 to 1.0 | Sequential | RAST annotation consistency |

### Track Data Types

**Sequential (continuous numeric):**
- Use gradient color scale (e.g., white → blue → red)
- Example: Gene length, conservation fraction

**Categorical:**
- Use distinct colors for each category
- Example: Gene direction (+/−), Pangenome conservation (core/aux/other)

**Diverging (centered on zero):**
- Use diverging color scale (e.g., blue → white → red)
- Example: Flux values (negative/zero/positive)

---

## 4. UI/UX Requirements

### 4.1 Track Control Panel (Left Side)

**Functionality:**
- Checkbox to show/hide each track
- Sort button next to each track to sort genes by that track
- Ability to reorder tracks (drag and drop?)
- "Cluster by selected" button to cluster genes by multiple tracks

**Quote from Christopher:**
> "The main advantage of adding and subtracting the data tracks... is probably to get one track to be next to another"

### 4.2 Zoom Functionality

**Requirements:**
- Genome selector at bottom (like a scrollbar/range selector)
- Click and drag to select region
- Zoom in to see fewer genes in more detail
- Reset button to zoom back out
- When zoomed in enough, show actual gene names/IDs

**Quote from Christopher:**
> "What would be really cool is if you could zoom in all the way until you actually see what the genes and the functions are"

### 4.3 Sorting

**Requirements:**
- Click sort button on any track to sort all genes by that track's values
- Maintains alignment across all tracks
- Should support ascending/descending

**Quote from Christopher:**
> "There might be a button here where you would sort by a particular track... it would resort the order of the genes based on what your criteria was"

### 4.4 Clustering

**Requirements:**
- Select multiple tracks
- Click "Cluster" button
- Genes are grouped by similarity across selected tracks
- Visual indication of cluster boundaries

**Quote from Christopher:**
> "There might be a button to cluster... you would select a bunch of things to cluster by and it would cluster the data by those tracks"

### 4.5 Hover/Click Interaction

**Requirements:**
- Hover over cell: Show tooltip with gene ID, track name, value
- Click on region: Expand to show gene details
- Click on gene: Show all data for that gene

**Quote from Christopher:**
> "Someone could see a part of the diagram that's interesting to them, and click on it and see the genes and maybe the data for those genes"

---

## 5. Data Sources & Integration

### 5.1 Primary Data Source

**Input:** `db.sqlite` file from a clade folder

**Location pattern:** `/path/to/pangenome/{clade_id}/db.sqlite`

**Current test data:** `/home/jplfaria/CDM_jose/ontology_data_utils/test_clade_s__Escherichia_coli/db.sqlite`

### 5.2 Tables in db.sqlite

**Currently defined (from datalake_table.py):**

```sql
-- Genome metadata
CREATE TABLE genome (
    genome TEXT PRIMARY KEY,
    gtdb_taxonomy TEXT NOT NULL,
    ncbi_taxonomy TEXT NOT NULL,
    n_contigs INT NOT NULL,
    n_features INT NOT NULL
);

-- ANI comparisons
CREATE TABLE ani (
    genome1 TEXT NOT NULL,
    genome2 TEXT NOT NULL,
    ani REAL NOT NULL,
    af1 REAL NOT NULL,
    af2 REAL NOT NULL,
    PRIMARY KEY (genome1, genome2)
);

-- User genome features
CREATE TABLE user_feature (
    genome TEXT NOT NULL,
    contig TEXT NOT NULL,
    feature_id TEXT NOT NULL,
    length INTEGER NOT NULL,
    start INTEGER NOT NULL,
    end INTEGER NOT NULL,
    strand TEXT NOT NULL,
    type TEXT NOT NULL,
    sequence TEXT NOT NULL,
    sequence_hash TEXT NOT NULL,
    pangenome_cluster TEXT NOT NULL,
    pangenome_is_core INTEGER NOT NULL,
    PRIMARY KEY (genome, contig, feature_id)
);

-- Pangenome features (reference genomes)
CREATE TABLE pangenome_feature (
    genome TEXT NOT NULL,
    contig TEXT NOT NULL,
    feature_id TEXT NOT NULL,
    length INTEGER NOT NULL,
    start INTEGER NOT NULL,
    end INTEGER NOT NULL,
    strand TEXT NOT NULL,
    type TEXT NOT NULL,
    sequence TEXT NOT NULL,
    sequence_hash TEXT NOT NULL,
    pangenome_cluster TEXT NOT NULL,
    pangenome_is_core INTEGER NOT NULL,
    PRIMARY KEY (genome, contig, feature_id)
);
```

### 5.3 Additional Tables Needed

For the full heatmap, these tables need to be added/populated:

```sql
-- Gene fitness data (from fitness.py)
CREATE TABLE gene_fitness (
    genome_id TEXT NOT NULL,
    feature_id TEXT NOT NULL,
    fitness_genome_id TEXT NOT NULL,
    fitness_feature_id TEXT NOT NULL,
    set_id TEXT NOT NULL,
    value REAL NOT NULL
);

-- Phenotype simulation results
CREATE TABLE gene_phenotype (
    genome_id TEXT NOT NULL,
    feature_id TEXT NOT NULL,
    phenotype_id TEXT NOT NULL,
    growth REAL NOT NULL,
    is_essential INTEGER NOT NULL
);

-- FVA results
CREATE TABLE gene_fva (
    genome_id TEXT NOT NULL,
    feature_id TEXT NOT NULL,
    reaction_id TEXT NOT NULL,
    media TEXT NOT NULL,  -- 'minimal' or 'rich'
    classification TEXT NOT NULL  -- 'blocked', 'active', 'essential'
);

-- RAST annotation scores
CREATE TABLE gene_annotation (
    genome_id TEXT NOT NULL,
    feature_id TEXT NOT NULL,
    rast_function TEXT,
    consensus_score REAL,
    specificity_score REAL
);
```

### 5.4 Computing Derived Tracks

**Pangenome conservation fraction:**
```sql
SELECT
    f.feature_id,
    f.pangenome_cluster,
    (SELECT COUNT(DISTINCT genome)
     FROM pangenome_feature pf
     WHERE pf.pangenome_cluster = f.pangenome_cluster) * 1.0 /
    (SELECT COUNT(DISTINCT genome) FROM pangenome_feature) AS conservation_fraction
FROM user_feature f
```

**Number of fitness scores above threshold:**
```sql
SELECT
    feature_id,
    COUNT(*) AS n_fitness_above_threshold
FROM gene_fitness
WHERE value > 0.5  -- threshold
GROUP BY genome_id, feature_id
```

---

## 6. Two View Modes

Christopher mentioned the same UI should support two different views:

### 6.1 Genome View (Genes × Data Tracks)

- **X-axis:** Genes in one genome (4,000+ genes)
- **Y-axis:** Data tracks (14+ tracks)
- **Use case:** Explore functional data for a single genome

### 6.2 Phenotype View (Genomes × Phenotypes)

- **X-axis:** Genomes in the pangenome (100+ genomes)
- **Y-axis:** Phenotypes (150+ phenotypes)
- **Each cell:** Growth/no-growth or fitness value
- **Use case:** Compare phenotype profiles across genomes

**Quote from Christopher:**
> "The same exact UI would be rendered, but the axes would be different... It's the same exact UI, it's just different data"

### 6.3 Shared UI Component

The heatmap renderer should be **generic**:
- Takes a matrix of data
- Takes row labels (genes or genomes)
- Takes column labels (tracks or phenotypes)
- Renders the heatmap with all interactive features

---

## 7. Current State of Codebase

### 7.1 Repository Structure

**Main repo:** https://github.com/kbaseapps/KBDatalakeApps

**Local clone:** `/home/jplfaria/repos/KBDatalakeApps`

### 7.2 Existing Components

| Component | File | Status |
|-----------|------|--------|
| HTML viewer (basic) | `/data/html/index.html` | EXISTS - DataTables viewer |
| JS/CSS assets | `/data/html/assets/` | EXISTS - Vite-built bundle |
| Table builder | `berdl/berdl/tables/datalake_table.py` | PARTIAL - schemas defined |
| Fitness data loader | `berdl/berdl/fitness.py` | NEW - just added |
| Ontology tables | `lib/KBDatalakeApps/KBDatalakeUtils.py` | DONE - Jose's PR merged |
| Pangenome pipeline | `berdl/berdl/pangenome/pangenome.py` | EXISTS |
| RAST annotation | `annotation/annotation.py` | EXISTS |

### 7.3 Existing HTML Viewer

The current viewer at `/data/html/` is a **DataTables viewer** (tabular data), NOT a heatmap. It uses:
- Vite for bundling
- Likely Vue.js or similar (based on `<div id="app">`)
- Bootstrap icons
- Custom CSS

This is **NOT** what Christopher wants for the heatmap - a new visualization component needs to be built.

### 7.4 Test Database

**Location:** `/home/jplfaria/CDM_jose/ontology_data_utils/test_clade_s__Escherichia_coli/db.sqlite`

**Size:** 210 MB

**Contains:** E. coli genome features, but likely missing:
- Fitness data
- Phenotype data
- FVA classifications
- Consensus scores

---

## 8. Blockers & Dependencies

### 8.1 Reference Data Sync (CRITICAL BLOCKER)

**Problem:** The production system at `/data/reference_data/` doesn't have all required files.

**Required files:**
1. `seed.json` - RAST → seed.role mapping (15 MB)
2. `statements.parquet` - Ontology labels/definitions (328 MB)
3. `kegg_ko_definitions.parquet` - KEGG definitions (928 KB)
4. `cog_definitions.parquet` - COG definitions (194 KB)
5. `kegg_ko_ec_mapping.tsv` - KEGG→EC mapping (222 KB)
6. `phenotype_data/fitness_genomes/` - Fitness JSON files (???)

**Who can fix:** Boris needs to sync/deploy these files

**Quote from Christopher:**
> "Boris needs to deploy... sync the reference data before I can run any of the phenotype stuff"

### 8.2 Populated Test Data

**Problem:** Jose needs a fully populated `db.sqlite` to build the visualization

**What Christopher promised:**
> "I'll try to get you ADP1 data with a bunch of these populated today"

**Current state:** Only basic genome features exist, missing phenotype/fitness/FVA data

### 8.3 Philippe's Work

**Unknown:** Philippe is working on something related, but Christopher doesn't know the details

**Quote from Christopher:**
> "Philippe is doing things, but I don't know what Philippe is doing"

---

## 9. Implementation Phases

### Phase 1: Basic Heatmap Renderer (Can Start Now)

**Goal:** Build the visualization component with mock/available data

**Tasks:**
1. Create heatmap rendering component (Canvas or SVG)
2. Implement track toggle (show/hide)
3. Implement basic zoom (range selector)
4. Implement sort by track
5. Test with available data (gene length, direction, pangenome conservation)

**Data available now:**
- Gene order (from `start` position)
- Gene length
- Gene direction (strand)
- Pangenome cluster ID
- Pangenome is_core flag

### Phase 2: Data Integration (When Data Available)

**Goal:** Connect to full database with all tracks

**Tasks:**
1. Add fitness track (from `gene_fitness` table)
2. Add phenotype count track
3. Add FVA classification tracks
4. Add consensus score track
5. Compute derived tracks (conservation fraction, etc.)

### Phase 3: Advanced Features

**Goal:** Full interactive experience

**Tasks:**
1. Implement clustering
2. Add click-to-zoom-to-gene
3. Add gene detail panel
4. Implement phenotype view mode
5. Polish UI/UX

---

## 10. Technical Architecture

### 10.1 Recommended Technology Stack

**Frontend:**
- **Rendering:** D3.js or Canvas API (for performance with 4,000+ genes)
- **Framework:** Vue.js (matches existing `/data/html/` setup) or vanilla JS
- **Build:** Vite (already used)
- **Styles:** Tailwind CSS or Bootstrap

**Data Loading:**
- Read `db.sqlite` via JavaScript SQLite library (sql.js)
- Or: Pre-export to JSON for static HTML report

### 10.2 Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   db.sqlite     │ ──► │  Data Loader    │ ──► │  Heatmap        │
│   (SQLite)      │     │  (JS/Python)    │     │  Renderer       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Track Matrix   │
                        │  {              │
                        │    genes: [...],│
                        │    tracks: [...],│
                        │    values: [[]] │
                        │  }              │
                        └─────────────────┘
```

### 10.3 Output Format

**Standalone HTML Report:**
- Single `index.html` file
- Embedded JS/CSS (or bundled assets folder)
- Embedded data (JSON) or loads from file
- Works offline in browser

**Integration with KBase:**
- Report saved via `KBaseReport.create_extended_report()`
- HTML served as report attachment
- `db.sqlite` available for download

---

## Appendix A: Key Quotes from Christopher

### On the visualization:
> "It's a heat map. It's a big heat map."

### On tracks:
> "Like bands of data, and it may be like a heat map, or it may be like a line graph, like it depends on what the data is."

### On zooming:
> "What would be really cool is if you could zoom in all the way until you actually see what the genes and the functions are."

### On track control:
> "The main advantage of the adding and subtracting the data tracks... is probably to get one track to be next to another."

### On sorting:
> "There might be a button here where you would sort by a particular track and... it would resort the order of the genes based on what your criteria was."

### On reusability:
> "The same exact UI would be rendered, but the axes would be different... it's just different data."

### On timeline:
> "We kind of need the visualizations for Adam."

---

## Appendix B: Reference to Vibhav's App

Christopher repeatedly references "Vibhav's app" or "Vibhav's viewer" as a UI inspiration. This appears to be an existing KBase tool with:
- Tabular data display
- Column toggle (show/hide)
- Filtering capabilities

The heatmap viewer should have similar track toggle behavior but render as a heatmap instead of a table.

---

## Appendix C: Files to Review

1. **Transcript:** `/home/jplfaria/CDM_jose/ontology_data_utils/heatmap.txt`
2. **Whiteboard image:** `/home/jplfaria/CDM_jose/ontology_data_utils/heatmap?.png`
3. **Current HTML viewer:** `/home/jplfaria/repos/KBDatalakeApps/data/html/`
4. **Table schemas:** `/home/jplfaria/repos/KBDatalakeApps/berdl/berdl/tables/datalake_table.py`
5. **Fitness loader:** `/home/jplfaria/repos/KBDatalakeApps/berdl/berdl/fitness.py`
6. **Test database:** `/home/jplfaria/CDM_jose/ontology_data_utils/test_clade_s__Escherichia_coli/db.sqlite`

---

## 11. Implementation Progress (Prototype v1)

### 11.1 Files Created

**Location:** `/home/jplfaria/CDM_jose/ontology_data_utils/heatmap_viewer/`

| File | Size | Description |
|------|------|-------------|
| `index.html` | 16 KB | Main heatmap viewer (requires server for data) |
| `heatmap_standalone.html` | 395 KB | Self-contained version with embedded data |
| `genes_data.json` | 374 KB | Extracted gene data (4,617 genes) |
| `view_heatmap.ipynb` | 1 KB | Jupyter notebook to view inline |

### 11.2 Features Implemented

**UI Style:** Light theme matching DataTables viewer (tables.png reference)

| Feature | Status | Notes |
|---------|--------|-------|
| Canvas-based heatmap rendering | ✅ Done | Handles 4,617 genes |
| Sidebar with track checkboxes | ✅ Done | Like "Other Attributes" in DataTables |
| Track toggle (show/hide) | ✅ Done | Checkboxes control visibility |
| Sort by track | ✅ Done | "Sort ↓" button on hover |
| Zoom slider | ✅ Done | 1x to 100x zoom |
| Position slider | ✅ Done | Scroll through genome |
| Reset zoom button | ✅ Done | Returns to full view |
| Tooltip on hover | ✅ Done | Shows gene details |
| Select all / Deselect all | ✅ Done | Quick actions |
| Reset to genome order | ✅ Done | Clears sorting |
| Legend | ✅ Done | Shows color meanings |
| Track labels in heatmap | ✅ Done | Left side of canvas |

### 11.3 Data Tracks Configured

| # | Track | Type | Data Source | Enabled by Default |
|---|-------|------|-------------|-------------------|
| 1 | Gene Order | Sequential | genome_features.id | ✅ |
| 2 | Gene Length | Sequential | genome_features.length | ✅ |
| 3 | Gene Direction | Binary | genome_features.strand | ✅ |
| 4 | Pangenome Conservation | Sequential | Computed fraction | ✅ |
| 5 | Core/Accessory | Categorical | pangenome_is_core | ✅ |
| 6 | # KEGG Terms | Sequential | ontology_terms count | ☐ |
| 7 | # COG Terms | Sequential | ontology_terms count | ☐ |
| 8 | # Pfam Terms | Sequential | ontology_terms count | ☐ |
| 9 | # GO Terms | Sequential | ontology_terms count | ☐ |
| 10 | Subcellular Localization | Categorical | psortb | ☐ |

### 11.4 Color Scheme

- **Sequential values:** Blue (#3b82f6) → Red (#ff3232) gradient
- **Binary (strand):** Green (#22c55e) for +, Red (#ef4444) for −
- **Categorical:** Gray (#9ca3af) Unknown, Orange (#f59e0b) Accessory, Green (#22c55e) Core

### 11.5 How to View

**Option 1 - JupyterLab (recommended):**
1. Open `/home/jplfaria/CDM_jose/ontology_data_utils/heatmap_viewer/view_heatmap.ipynb`
2. Run the second cell to display inline

**Option 2 - Standalone HTML:**
1. Right-click `heatmap_standalone.html` in JupyterLab file browser
2. Select "Open in New Browser Tab"

**Option 3 - HTTP Server (if accessible):**
```bash
cd /home/jplfaria/CDM_jose/ontology_data_utils/heatmap_viewer
python3 -m http.server 8889
# Then open http://localhost:8889
```

### 11.6 Remaining Work (Future)

| Feature | Priority | Notes |
|---------|----------|-------|
| Clustering by selected tracks | Medium | Requires implementing k-means or hierarchical |
| Click to zoom to region | Medium | Select region and expand |
| Gene detail panel | Low | Click gene to see all data |
| Phenotype view mode | Low | Genomes × Phenotypes matrix |
| Export PNG/SVG | Low | Download visualization |
| Integration with KBDatalakeApps | TBD | Move to /data/html/ structure |

### 11.7 Data Extraction Query

Gene data was extracted from `db.sqlite` using:

```python
# Key query to get gene data with pangenome conservation
SELECT
    gf.id, gf.feature_id, gf.length, gf.start, gf.strand,
    CAST(pc.cluster_count AS REAL) / 42.0 as conservation_fraction,
    CASE WHEN gf.pangenome_is_core = 1 THEN 2
         WHEN gf.pangenome_cluster_id IS NOT NULL THEN 1
         ELSE 0 END as pan_category,
    gf.rast_function,
    COUNT(CASE WHEN ot.namespace='KEGG.ORTHOLOGY' THEN 1 END) as n_ko,
    COUNT(CASE WHEN ot.namespace='eggNOG.COG' THEN 1 END) as n_cog,
    COUNT(CASE WHEN ot.namespace='Pfam' THEN 1 END) as n_pfam,
    COUNT(CASE WHEN ot.namespace LIKE 'GO%' THEN 1 END) as n_go,
    psortb_localization
FROM genome_features gf
LEFT JOIN ontology_terms ot ON gf.feature_id = ot.feature_id
LEFT JOIN (SELECT pangenome_cluster_id, COUNT(*) as cluster_count
           FROM pan_genome_features GROUP BY pangenome_cluster_id) pc
    ON gf.pangenome_cluster_id = pc.pangenome_cluster_id
WHERE gf.genome = 'GCF_000005845.2'
GROUP BY gf.id
ORDER BY gf.start
```

---

*Document generated by Claude Code Assistant, February 10, 2026*
