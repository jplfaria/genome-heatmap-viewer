# Genome Heatmap Viewer

An interactive web-based visualization tool for exploring bacterial genome annotations, pangenome data, metabolic modeling, and phenotype predictions. Built for KBase integration.

**Current Dataset:** Acinetobacter baylyi ADP1 + 13 reference genomes

## 🎯 Features

### Multi-Tab Interface
- **Tracks Tab** - Main heatmap with 38 configurable tracks
- **Distributions Tab** - Statistical distributions for all tracks
- **Tree Tab** - UPGMA phylogenetic dendrogram with genome statistics
- **Cluster Tab** - UMAP scatter plot for gene clustering
- **Metabolic Map Tab** - Interactive Escher pathway maps with flux predictions
- **Help Tab** - Comprehensive built-in documentation

### Data Coverage
- **3,235 genes** × 38 fields = ~175,000 data points
- **Pangenome:** Core/Accessory classification, conservation across 13 reference genomes
- **Annotations:** RAST, Bakta, KO, COG, Pfam, GO, EC terms with consistency scores
- **Metabolic:** 1,279 reactions, FBA flux predictions, gapfilling analysis
- **Phenotypes:** Fitness scores, essentiality, growth predictions

## 🚀 Quick Start

### Standalone Viewer

```bash
git clone <repository-url>
cd genome-heatmap-viewer

# Serve locally
python3 -m http.server 8000

# Open http://localhost:8000
```

### KBase Deployment

```bash
# Sync viewer to KBase repo
./sync-to-kbase.sh

# Deploy to AppDev
cd ~/repos/KBDatalakeDashboard
git add data/heatmap/
git commit -m "Update heatmap viewer"
git push  # Auto-deploys

# Test at https://ci.kbase.us
```

## 📊 Data Generation

### Prerequisites
- BERDL SQLite database (`berdl_tables.db`)
- Python 3.8+, numpy, scipy, umap-learn

### Generate All Data Files

```bash
# Core data (required)
python3 generate_metadata.py          # Organism metadata
python3 generate_genes_data.py        # Main gene data (3,235 × 38)
python3 generate_tree_data.py         # UPGMA phylogenetic tree
python3 generate_cluster_data.py      # UMAP embeddings
python3 generate_summary_stats.py     # Summary statistics

# Extended data (optional)
python3 generate_reactions_data.py             # Metabolic reactions
python3 extract_pan_genome_features.py        # Reference genome stats
```

### Validation

```bash
# Spot-check 10 random genes
python3 validate_genes_data.py

# Comprehensive data integrity check
python3 validate_data_integrity.py
```

**Expected:** All checks pass ✅

## 🎨 Color Schemes (Colorblind-Safe)

### Pangenome Categories
- 🟢 **Green** - Core genes (>95% genomes)
- 🟠 **Orange** - Accessory genes (5-95%)
- ⚪ **Gray** - Unknown (<5% or no cluster)

### Consistency Scores
- 🟠 **Orange** - High agreement (1.0)
- 🔵 **Blue** - Low agreement (0.0)
- ⚪ **Gray** - N/A (no cluster)

### Binary Tracks
- 🟣 **Purple** - Forward strand / True
- 🟠 **Orange** - Reverse strand / False

## 📁 Key Files

```
genome-heatmap-viewer/
├── index.html                      # Main viewer (pure HTML/CSS/JS)
├── config.json                     # Track definitions & UI config
├── genes_data.json                 # Gene data (3,235 × 38 fields, 585 KB)
├── tree_data.json                  # UPGMA phylogenetic tree
├── cluster_data.json               # UMAP embeddings
├── reactions_data.json            # Metabolic reaction data
├── ref_genomes_data.json          # Reference genome statistics
├── metabolic_map_*.json           # Escher pathway maps
├── generate_*.py                   # Data generation scripts (11 total)
├── validate_*.py                   # Validation scripts (2 total)
├── QA_VALIDATION_REPORT.md        # Comprehensive validation results
└── tests/viewer.spec.js           # Playwright tests (80+ tests)
```

## 🧪 Testing

### Automated Tests

```bash
npm install
npm test  # Run 80+ Playwright tests
```

### Manual Workflows

1. **Characterization Targets** - Find core genes with unknown function
2. **Metabolic Gap Analysis** - Identify missing reactions
3. **Annotation Quality** - Compare RAST vs Bakta consistency

See `QA_VALIDATION_REPORT.md` for detailed test procedures.

## 🔍 Data Fields (38 total)

### Core
- ID, FID (locus tag), FUNC, LENGTH, START, STRAND, PROT_LEN

### Pangenome
- CONS_FRAC (conservation 0-1), PAN_CAT (0=Unknown, 1=Accessory, 2=Core), CLUSTER_SIZE

### Consistency (-1=N/A, 0-1 scale)
- AVG_CONS, RAST_CONS, KO_CONS, GO_CONS, EC_CONS, BAKTA_CONS, EC_MAP_CONS, SPECIFICITY

### Annotation Depth
- N_KO, N_COG, N_PFAM, N_GO, N_EC, N_MODULES, HAS_NAME, IS_HYPO

### Localization
- LOC (Cytoplasmic/Periplasmic/Membrane/Extracellular)

### Metabolic
- REACTIONS, RICH_FLUX, MIN_FLUX, RICH_CLASS, MIN_CLASS

### Phenotype
- ESSENTIALITY, N_PHENOTYPES, N_FITNESS

## 🔧 Troubleshooting

### "Colors don't match Help documentation"
✅ **Fixed!** All color documentation corrected in latest version.

### "Tree shows wrong gene counts"
✅ **Fixed!** Regenerate `tree_data.json` with updated script.

### "KBase deployment fails with module name error"
✅ **Fixed!** `spec.json` now uses `KBDatalakeDashboard2` (with '2').

### "Missing core count seems wrong"
✅ **Fixed!** Now uses correct computation from `ref_genomes_data.json`.

### "# Fitness Scores track shows no data"
⚠️ **Known Limitation:** Fitness data not available for all organisms. Track marked as placeholder (*) when source data unavailable.

## ✅ QA Validation Status

**Last Validated:** 2026-02-16

- ✅ 10/10 random genes validated against database
- ✅ All field ranges within biological limits
- ✅ Color schemes corrected (Green=Core, Orange/Blue consistency)
- ✅ Missing core computation fixed
- ✅ Tree n_genes now counts actual genes (not clusters)
- ✅ All eukaryotic references removed
- ✅ No hardcoded E. coli references
- ✅ 80+ automated tests passing

**Pangenome Validation:**
- Core genes: 91.4% (high but valid for closely related strains)
- Conservation: 97.6% genes >0.9 (confirms close phylogeny)
- Consistency: 49.4% genes >0.7 (acceptable)
- Strand balance: 51.9% forward / 48.1% reverse ✓

See `QA_VALIDATION_REPORT.md` for comprehensive validation results.

## 📚 Documentation

- **README.md** (this file) - Getting started guide
- **QA_VALIDATION_REPORT.md** - Comprehensive validation results
- **ACTION_PLAN.md** - Development roadmap
- **PROJECT_STATUS.md** - Project status and data sources
- **Help Tab** - Built-in viewer documentation

## 👥 Credits

- **Christopher Henry** (chenry) - Requirements, data pipeline
- **Jose Faria** (jplfaria) - Development
- **Adam Arkin Lab** - Reference data, RB-TnSeq fitness data
- **Claude Sonnet 4.5** - QA validation assistant

## 📞 Support

- KBase support: https://www.kbase.us/support
- GitHub issues: <repository-url>/issues

## 📄 License

See KBase licensing terms.
