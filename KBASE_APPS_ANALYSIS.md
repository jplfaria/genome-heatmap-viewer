# KBDatalakeApps - Deep Technical Analysis

**Repository:** https://github.com/jplfaria/KBDatalakeApps
**Local Path:** `~/repos/KBDatalakeApps`
**Purpose:** KBase narrative app that generates genome datalake data (feeds into KBDatalakeDashboard)

---

## Executive Summary

KBDatalakeApps is the **data generation backend** for the BERDL (Bacterial Expression Resource Data Lake) project. It processes user genomes through ANI analysis, functional annotation, metabolic modeling, and phenotype simulation, then packages all results into SQLite databases that power the genome heatmap dashboard.

**Relationship to Heatmap Viewer:** This app generates the `berdl_tables.db` SQLite files that contain the raw data we've been visualizing. Understanding this pipeline helps us properly integrate with the KBase ecosystem.

---

## 1. Architecture

### KBase SDK Module
- **Module name:** `KBDatalakeApps`
- **Owners:** chenry, jplfaria
- **Language:** Python 3.11+
- **Apps:** Single app `build_genome_datalake_tables`

### Data Pipeline
```
User Genome(s) in KBase
    ↓
ANI Analysis (SKANI vs 3 databases)
    ↓
Clade Assignment (GTDB taxonomy)
    ↓
Pangenome Cluster Mapping (TODO)
    ↓
Metabolic Model Building (COBRApy)
    ↓
Phenotype Simulation (FBA)
    ↓
SQLite Database Generation
    ↓
GenomeDataLakeTables object
    ↓
Dashboard HTML Report
```

---

## 2. Core Functionality

### Single KBase Method

**`build_genome_datalake_tables(params)`**

**Parameters:**
- `input_refs`: List of workspace refs (Genome or GenomeSet objects)
- `suffix`: String suffix for generated table names
- `save_models`: Boolean to save FBAModels to workspace
- `workspace_name`: Target workspace

**Execution Flow:**
1. Writes params to `input_params.json`
2. Calls `scripts/run_genome_pipeline.sh`
3. Pipeline activates `berdl_genomes` conda env
4. Runs `berdl/pipeline.py` (Python entry point)
5. Creates stub `GenomeDataLakeTables` object
6. Copies dashboard HTML and uploads to Shock
7. Returns KBase report with embedded viewer

**Current Status:** Partially implemented - core logic delegated to external scripts

---

## 3. BERDL Pipeline

### Entry Point

**Shell:** `scripts/run_genome_pipeline.sh`
```bash
conda activate berdl_genomes
python /kb/module/berdl/berdl/pipeline.py
```

**Python:** `berdl/pipeline.py`
```python
kbase_api = KBaseAPI(token)
genomes = extract_genomes_from_refs(input_refs)
genome_paths = GenomePaths(scratch_dir)
prep = BERDLPreGenome(genome_paths)
prep.run(genomes)  # ANI + clade assignment
```

### Step 1: Genome Preprocessing (BERDLPreGenome)

**Class:** `berdl/prep_genome_set.py:BERDLPreGenome`

**Method: `run(genomes)`**
1. **`pre_user_genomes()`**
   - Downloads assemblies to FASTA
   - Downloads genes to FASTA
   - Writes `library_user_genomes` list

2. **`run_ani_databases()`**
   - Runs SKANI against 3 sketch databases:
     - `fast_kepangenome` - GTDB representatives
     - `fast_fitness` - Fitness experiment genomes
     - `fast_phenotypes` - Phenotype experiment genomes
   - Returns ANI DataFrames (ani, align_frac_ref, align_frac_query)

3. **`ani_translate_clade()`**
   - Maps NCBI assembly IDs → GTDB representative IDs
   - Structure: `{user_genome: {gtdb_clade: [ani, af_ref, af_query]}}`

4. **`match_top_clade()`**
   - Finds best GTDB clade per user genome
   - Returns `{user_genome: best_gtdb_clade}` mapping

5. **Saves `user_to_clade.json`**

**Output:**
- `user_to_clade` dict - genome → clade assignments
- `ani_clades` dict - full ANI results
- `df_ani_fitness`, `df_ani_phenotype` - fitness/phenotype ANI data

### Step 2: Pangenome Analysis (TODO - Stub)

**Class:** `berdl/pangenome.py:BERDLPangenome`

**Intended Logic:**
1. Get representative genome for user genome
2. Get all members of that clade
3. Get all gene clusters in clade
4. Map genes to clusters
5. Build master protein alignment

**Current Status:** Empty stub - NOT implemented

**Missing Functionality:**
- Conservation fraction calculation
- Core/accessory/unique classification
- Consistency score computation
- These are the fields we need for the heatmap!

---

## 4. Full Pipeline Implementation (KBDatalakeUtils)

### Class: `lib/KBDatalakeApps/KBDatalakeUtils.py:KBDataLakeUtils`

**Inherits from 5 KBUtilLib utility classes:**
- Workspace operations
- Genome operations
- Model operations
- Annotation operations
- Report operations

### Method: `run_full_pipeline()`

**11 Pipeline Steps:**

#### Step 1: Process Arguments (line 74-124)
```python
pipeline_process_arguments_into_user_genome_table()
→ user_genomes.tsv (11 columns)
```

#### Step 2: Download Assemblies (line 164-214)
```python
pipeline_download_user_genome_assmemblies()
→ assemblies/<genome_id>.fasta
```

#### Step 3: Download Genes (line 271-385)
```python
pipeline_download_user_genome_genes()
→ genomes/<genome_id>.tsv
   Columns: contig, feature_id, start, end, strand, length,
            sequence, protein, rast_function, rast_functions,
            Annotation:SSO, Annotation:KO, Annotation:PFAM, etc.
```

#### Step 4: RAST Annotation (line 387-438)
```python
pipeline_annotate_user_genome_with_rast()
→ Adds rast_functions column to TSVs
```

#### Step 5: SKANI Analysis (line 216-263)
```python
pipeline_run_skani_analysis()
→ skani_pangenome.tsv
→ skani_fitness.tsv
→ skani_phenotype.tsv
```

#### Step 6: Build Models - Parallel (line 440-496)
```python
pipeline_run_moddeling_analysis()
→ Uses ProcessPoolExecutor
→ Calls _build_single_model_worker() per genome
→ Outputs models/<genome_id>.json
```

**Worker: `_build_single_model_worker()` (line 927-1065)**
```python
1. Load genome TSV
2. Create MSGenome object (ModelSEEDpy)
3. Build draft metabolic model
4. Run gapfilling on default media
5. Save model JSON
6. Return reaction/metabolite/gene counts
```

#### Step 7: Phenotype Simulations - Parallel (line 615-667)
```python
pipeline_run_phenotype_simulations()
→ Uses ProcessPoolExecutor
→ Calls _simulate_phenotypes_worker() per genome
→ Outputs phenotypes/<genome_id>_summary.tsv
```

**Worker: `_simulate_phenotypes_worker()` (line 1068-1138)**
```python
1. Load model JSON
2. Run FBA on Carbon-D-Glucose
3. Run FBA on minimal media
4. Test growth on phenotype media library
5. Compute accuracy metrics
6. Save summary TSV
```

#### Step 8: Build SQLite Database (line 721-829)
```python
pipeline_build_sqllite_db()
→ berdl_tables.db

Tables created:
  - genome (id, taxonomy, n_features)
  - genome_ani (genome1, genome2, ani, af1, af2, kind)
  - genome_features (feature_id, start, end, strand, function, etc.)
  - genome_accuracy
  - genome_gene_phenotype_reactions
  - genome_phenotype_gaps
  - gapfilled_reactions
```

#### Step 9: Save Genomes (line 504-576)
```python
pipeline_save_annotated_genomes()
→ Saves genomes to KBase workspace (production)
```

#### Step 10: Save Models (line 578-613)
```python
pipeline_save_models_to_kbase()
→ Saves FBAModels to workspace (production)
```

#### Step 11: Generate Report (line 838-924)
```python
pipeline_save_kbase_report()
→ Creates KBase report with embedded dashboard
```

---

## 5. Data Sources

### Reference Databases

**Location:** `/data/reference_data/`

**SKANI Sketch Libraries** (`skani_library/`):
- `fast_kepangenome` - GTDB representative genomes
- `fast_fitness` - Fitness experiment genomes
- `fast_phenotypes` - Phenotype experiment genomes

**Pangenome Parquet Tables** (`berdl_db/cdm_genomes/ke-pangenomes/block_*/`):
- `name.parquet` - Genome name lookups
- `contig.parquet` - Contig sequences
- `feature.parquet` - Gene features
- `protein.parquet` - Protein sequences
- `contig_x_feature.parquet` - Junction table
- `feature_x_protein.parquet` - Junction table

### BERDL API

**Class:** `berdl/berdl_api.py:BERDLApi`

**Endpoint:** `https://hub.berdl.kbase.us/apis/mcp/delta/tables/query`
**Auth:** Bearer token from environment
**Timeout:** 1200 seconds (20 minutes)

**Method: `sql(sql, page_limit, offset)`**
- Submits SQL query to BERDL Delta tables
- Returns JSON results

**Issue:** Notebook shows 55s timeout in practice

**Local Alternative:** `query/query_genome_local.py` reads parquet directly (1000x faster)

---

## 6. SQLite Database Schema

### Table: genome
**Columns:**
- `id` - Genome identifier
- `gtdb_taxonomy` - GTDB taxonomic lineage
- `ncbi_taxonomy` - NCBI taxonomic lineage
- `num_contigs` - Number of contigs
- `n_features` - Number of genes

**Source:** `user_genomes.tsv`

### Table: genome_ani
**Columns:**
- `genome1` - First genome ID
- `genome2` - Second genome ID
- `ani` - Average Nucleotide Identity (%)
- `af1` - Alignment fraction for genome1
- `af2` - Alignment fraction for genome2
- `kind` - Database ("pangenome", "fitness", "phenotype")

**Source:** SKANI TSV outputs

### Table: genome_features
**Columns:**
- `genome_id` - Genome identifier
- `contig_id` - Contig identifier
- `feature_id` - Gene/feature identifier
- `length` - Gene length (bp)
- `start` - Start position
- `end` - End position
- `strand` - Strand (+/-)
- `sequence` - DNA sequence
- `sequence_hash` - MD5 hash of sequence
- `rast_function` - RAST functional annotation
- `rast_functions` - Alternative RAST annotations
- `protein_translation` - Amino acid sequence
- `ontology_terms` - Semicolon-separated ontology IDs

**Source:** `genomes/<genome_id>.tsv` files

### Table: genome_accuracy
**Source:** Phenotype simulation accuracy metrics

### Table: genome_gene_phenotype_reactions
**Source:** Gene-to-reaction mappings from models

### Table: genome_phenotype_gaps
**Source:** Missing metabolic capabilities

### Table: gapfilled_reactions
**Source:** Computationally added reactions

---

## 7. Data Mapping: SQLite → genes_data.json

### Current genes_data.json Fields
```javascript
[id, fid, length, start, strand, conservation_frac, pan_category, function,
 n_ko, n_cog, n_pfam, n_go, localization, rast_cons, ko_cons, go_cons,
 ec_cons, avg_cons, bakta_cons, ec_avg_cons, specificity]
```

### Available from SQLite

**Direct mapping:**
- `id` ← row index
- `fid` ← `feature_id`
- `length` ← `length` (or `end - start`)
- `start` ← `start`
- `strand` ← `strand` (convert +/- to 1/-1)
- `function` ← `rast_function`

**Parseable from ontology_terms:**
- `n_ko` ← count "KO:" prefixed terms
- `n_cog` ← count "COG:" prefixed terms
- `n_pfam` ← count "PFAM:" prefixed terms
- `n_go` ← count "GO:" prefixed terms

### Missing from SQLite

**Pangenome fields** (requires pangenome analysis):
- `conservation_frac` - Fraction of genomes with ortholog
- `pan_category` - Core (2) / Accessory (1) / Unique (0)

**Annotation consistency** (requires cluster-based comparison):
- `rast_cons` - RAST function agreement in cluster
- `ko_cons` - KO term agreement in cluster
- `go_cons` - GO term agreement in cluster
- `ec_cons` - EC number agreement in cluster
- `bakta_cons` - Bakta annotation agreement
- `avg_cons` - Average of all consistency scores
- `ec_avg_cons` - EC consistency average

**Annotation quality:**
- `localization` - PSortB cellular compartment (client exists but not used)
- `specificity` - Annotation specificity metric (not in DB)

### Where This Data Should Come From

**Consistency scores:**
- Requires pangenome cluster membership
- For each gene, get its cluster
- Get all genes in that cluster from other genomes
- Compare annotations across cluster members
- Calculate agreement percentage

**Conservation fraction:**
- Count how many genomes have gene in this cluster
- Divide by total genomes in pangenome

**Pan category:**
- If conservation_frac > 0.95: Core (2)
- If conservation_frac >= 0.05: Accessory (1)
- If conservation_frac < 0.05: Unique/Singleton (0)

**Localization:**
- PSortB client initialized at line 102
- Not currently invoked in pipeline
- Would need to add annotation step

---

## 8. Notebooks

### genomes.ipynb

**Purpose:** Development testing of BERDL components

**Key Demos:**

**ANI Analysis:**
```python
prep = BERDLPreGenome(paths)
prep.run(['R12', '3H11'])
# Results:
# Rhodanobacter-sp → RS_GCF_021545845.1 (100% ANI)
# Acidovorax-sp → RS_GCF_001633105.1 (99.99% ANI)
```

**BERDL API Testing:**
```python
api = BERDLApi()
result = api.sql("SELECT * FROM kbase_genomes.name WHERE name = 'GB_GCA_019459165.1'")
# Result: 55s timeout (despite 1200s setting)
```

**Local Parquet Query:**
```python
query = QueryGenomeLocal(parquet_dir)
result = query.get_genome_by_name('GB_GCA_019459165.1')
# Result: 51.3ms (1000x faster than API)
```

### test_pipeline_steps.ipynb

**Purpose:** Step-by-step pipeline testing

**Architecture:**
- Uses `util.py` to load KBase token
- Fresh `KBDataLakeUtils` per cell
- Saves config to datacache for reloading

**Cells test each of 11 pipeline steps independently**
- Allows isolated debugging
- Shows intermediate outputs
- Validates data flow

**Example:**
```python
# Cell: Step 3 - Download Genes
util.pipeline_download_user_genome_genes()
# Output: genomes/<genome_id>.tsv with 18 columns
# Preview: First 5 rows with feature_id, function, ontology terms
```

---

## 9. Integration with KBDatalakeDashboard

### Data Flow

```
KBDatalakeApps (this repo)
    ↓ generates
GenomeDataLakeTables object
    ├─ pangenome_data[]
    │   └─ sqllite_tables_handle_ref → Shock file
    │       └─ berdl_tables.db
    └─ (metadata)

KBDatalakeDashboard (viewer)
    ↓ reads via
TableScanner Service
    ↓ queries
SQLite database in Shock
    ↓ returns
Table rows as JSON
    ↓ renders
Interactive dashboard
```

### Current Gap

**Problem:** Pangenome analysis is incomplete

**Impact:** SQLite lacks:
- Cluster assignments
- Conservation fractions
- Consistency scores

**Solution path:**
1. Implement `BERDLPangenome.run()` in `berdl/pangenome.py`
2. Query local parquet files or BERDL API for cluster data
3. Add cluster membership to `genome_features` table
4. Calculate consistency scores during pangenome step
5. Add new columns to SQLite schema

---

## 10. Next Steps for Integration

### Phase 1: Understand Data Format
✅ **Complete** - We now understand:
- How data is generated (pipeline)
- What's in SQLite (schema)
- What's missing (pangenome fields)
- How dashboard consumes it (TableScanner API)

### Phase 2: Add Heatmap to Dashboard
**Approach:** Modify KBDatalakeDashboard to include heatmap HTML

**Steps:**
1. Create heatmap HTML in KBDatalakeDashboard repo
2. Configure to read UPA from app-config.json
3. Fetch data from TableScanner API
4. Transform to genes_data.json format
5. Render heatmap

### Phase 3: Complete Pangenome Pipeline (Optional)
**If we need full consistency scores:**
1. Implement `BERDLPangenome` class
2. Add cluster queries
3. Calculate consistency scores
4. Update SQLite schema
5. Redeploy KBDatalakeApps

**Alternative:** Calculate consistency scores client-side in JavaScript

---

## Summary

**KBDatalakeApps Status:**
- ✅ Core infrastructure complete
- ✅ Full pipeline implemented (KBDatalakeUtils)
- ⏳ Main SDK app uses simplified pipeline
- ❌ Pangenome analysis incomplete (stub)
- ✅ Dashboard HTML embedded and configured

**Key Takeaway:**
This repo generates the `berdl_tables.db` SQLite files that power our genome heatmap viewer. To fully integrate with KBase, we need to either:
1. Complete the pangenome pipeline to generate missing fields, OR
2. Calculate those fields client-side in the heatmap viewer

**Recommended:** Start with client-side calculation for faster iteration, then optimize with server-side if needed.

