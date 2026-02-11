# Agent Handoff Document

**Project:** Genome Heatmap Viewer
**Date:** February 11, 2026
**Previous Agent:** Claude Code (Opus 4.5)
**Purpose:** Enable another agent to continue development from this point

---

## Project Context

This is a **multi-track genome heatmap visualization tool** requested by Christopher Henry (KBase) for visualizing genomic and phenotypic data. It's designed to complement the existing DataTables viewer in KBDatalakeApps.

**Key Stakeholders:**
- Christopher Henry - Project lead, provided requirements
- Jose Faria (jplfaria) - Developer
- Adam - End user (needs visualizations for paper/presentation)

---

## Current State

### What's Working

1. **Heatmap Viewer Prototype** (`index.html`)
   - Canvas-based rendering for 4,617 genes
   - 12 data tracks implemented, 6 placeholders
   - Track toggle (show/hide via checkboxes)
   - Sort by any track
   - Zoom (1x-100x) and position slider
   - Hover tooltips with gene details
   - Light theme matching DataTables viewer style

2. **Data Pipeline**
   - Gene data extracted from `berdl_tables_ontology_terms.db`
   - Pangenome conservation fraction computed
   - Consistency scores integrated (rast, ko, go, ec, bakta, avg)
   - Annotation specificity derived

3. **Viewing Options**
   - Standalone HTML with embedded data
   - HTTP server mode
   - Jupyter notebook inline display

### What's NOT Working / Incomplete

1. **Placeholder Tracks** (data not yet available):
   - Neighborhood Conservation - awaiting BERDL pipeline
   - Flux (minimal/rich media) - requires FBA results
   - Reaction Classification - requires FVA results
   - Phenotype Count - requires model-gene-phenotype mapping
   - Fitness Score Count - requires fitness.py integration

2. **Advanced Features** (not yet implemented):
   - Clustering by selected tracks
   - Click-to-zoom-to-region
   - Gene detail panel
   - Phenotype view mode (Genomes × Phenotypes)
   - Export PNG/SVG

3. **Integration**:
   - Not yet integrated into KBDatalakeApps repo
   - No automated data extraction script

---

## File Structure

```
genome-heatmap-viewer/
├── index.html              # Main viewer (24KB)
├── heatmap_standalone.html # Self-contained with embedded data (706KB)
├── genes_data.json         # Gene data array (682KB, 4617 genes)
├── view_heatmap.ipynb      # Jupyter notebook for inline viewing
├── README.md               # User documentation
├── AGENT_HANDOFF.md        # This file
├── HEATMAP_VIEWER_REQUIREMENTS.md  # Full requirements from Christopher
└── notebooks/
    └── test_generate_ontology_tables.ipynb  # Data extraction notebook
```

---

## Key Code Sections

### Track Configuration (index.html ~line 50-90)

```javascript
const TRACKS = [
    // === BASIC GENE INFO ===
    { id: 'order', name: 'Gene Order', field: 0, type: 'sequential', enabled: true },
    { id: 'length', name: 'Gene Length', field: 2, type: 'sequential', enabled: true },
    { id: 'strand', name: 'Gene Direction', field: 4, type: 'binary', enabled: true },
    // === PANGENOME ===
    { id: 'conservation', name: 'Pangenome Conservation Fraction', field: 5, type: 'sequential', enabled: true },
    { id: 'pan_category', name: 'Core/Accessory', field: 6, type: 'categorical', enabled: true, categories: ['Unknown', 'Accessory', 'Core'] },
    // === CONSISTENCY SCORES ===
    { id: 'avg_cons', name: 'Function Consensus (avg)', field: 17, type: 'consistency', enabled: true },
    // ... more tracks
    // === PLACEHOLDERS ===
    { id: 'neighborhood', name: 'Neighborhood Conservation*', field: -1, type: 'placeholder', enabled: false },
    // ... more placeholders
];
```

### Color Scheme Functions (index.html ~line 100-140)

```javascript
const colorSchemes = {
    sequential: (v) => {
        // Blue (#3b82f6) to Red (#ff3232) gradient
        const r = Math.floor(59 + 196 * v);
        const g = Math.floor(130 - 80 * v);
        const b = Math.floor(246 - 196 * v);
        return `rgb(${r}, ${g}, ${b})`;
    },
    consistency: (v) => {
        // Red → Yellow → Green for -1 to 1 range
        if (v < 0) return '#e5e7eb';  // Gray for missing
        if (v < 0.5) {
            // Red to Yellow
            const r = 239;
            const g = Math.floor(68 + 180 * (v * 2));
            return `rgb(${r}, ${g}, 68)`;
        } else {
            // Yellow to Green
            const r = Math.floor(239 - 205 * ((v - 0.5) * 2));
            const g = Math.floor(248 - 52 * ((v - 0.5) * 2));
            return `rgb(${r}, ${g}, 68)`;
        }
    },
    // ... other schemes
};
```

### Data Format (genes_data.json)

Each gene is an array with 21 elements:
```
[id, fid, length, start, strand, conservation_frac, pan_category,
 function, n_ko, n_cog, n_pfam, n_go, localization,
 rast_cons, ko_cons, go_cons, ec_cons, avg_cons, bakta_cons,
 ec_avg_cons, specificity]
```

---

## Data Sources

### Primary Database
**File:** `/home/jplfaria/CDM_jose/ontology_data_utils/berdl_tables_ontology_terms.db`
**Size:** 148 MB
**Genome:** GCF_000005845.2 (E. coli K-12 MG1655)

### Key Tables

1. **genome_features**
   - Core gene data: id, feature_id, length, start, strand
   - Annotations: rast_function, psortb_localization
   - Consistency: rast_consistency, ko_consistency, go_consistency, ec_consistency, bakta_consistency, avg_consistency
   - Specificity: ko_other_annotations, go_other_annotations (JSON), annotation_specificity

2. **pan_genome_features**
   - cluster_id: Pangenome cluster assignment
   - Used to compute conservation_fraction

3. **ontology_terms**
   - namespace: KEGG.ORTHOLOGY, eggNOG.COG, Pfam, GO.*
   - Used to count term types per gene

### Data Extraction Query

```sql
SELECT
    gf.id, gf.feature_id, gf.length, gf.start, gf.strand,
    CAST(pc.cluster_count AS REAL) / 42.0 as conservation_fraction,
    CASE WHEN pgf.cluster_id IS NOT NULL AND pc.cluster_count > 40 THEN 2
         WHEN pgf.cluster_id IS NOT NULL THEN 1
         ELSE 0 END as pan_category,
    gf.rast_function,
    COUNT(CASE WHEN ot.namespace='KEGG.ORTHOLOGY' THEN 1 END) as n_ko,
    COUNT(CASE WHEN ot.namespace='eggNOG.COG' THEN 1 END) as n_cog,
    COUNT(CASE WHEN ot.namespace='Pfam' THEN 1 END) as n_pfam,
    COUNT(CASE WHEN ot.namespace LIKE 'GO.%' THEN 1 END) as n_go,
    gf.psortb_localization,
    COALESCE(gf.rast_consistency, -1) as rast_cons,
    COALESCE(gf.ko_consistency, -1) as ko_cons,
    COALESCE(gf.go_consistency, -1) as go_cons,
    COALESCE(gf.ec_consistency, -1) as ec_cons,
    COALESCE(gf.avg_consistency, -1) as avg_cons,
    COALESCE(gf.bakta_consistency, -1) as bakta_cons,
    COALESCE(gf.ec_avg_consistency, -1) as ec_avg_cons,
    COALESCE(gf.annotation_specificity, 0) as specificity
FROM genome_features gf
LEFT JOIN pan_genome_features pgf ON gf.feature_id = pgf.feature_id
LEFT JOIN (SELECT cluster_id, COUNT(*) as cluster_count
           FROM pan_genome_features GROUP BY cluster_id) pc
    ON pgf.cluster_id = pc.cluster_id
LEFT JOIN ontology_terms ot ON gf.feature_id = ot.feature_id
WHERE gf.genome = 'GCF_000005845.2'
GROUP BY gf.id
ORDER BY gf.start
```

---

## Related Work

### KBDatalakeApps Repository
**URL:** https://github.com/kbaseapps/KBDatalakeApps
**Local:** `/home/jplfaria/repos/KBDatalakeApps`

Relevant files:
- `lib/KBDatalakeApps/KBDatalakeUtils.py` - Ontology tables generation (has GO→EC extraction code)
- `berdl/berdl/tables/datalake_table.py` - Table schemas
- `data/html/` - Existing DataTables viewer

### GO → EC Extraction (PR #12)
Added extraction of EC numbers from GO terms via `oio:hasDbXref` predicate in statements.parquet.

---

## Next Steps (Suggested)

### Priority 1: Data Pipeline Automation
Create a Python script that:
1. Reads from `berdl_tables_ontology_terms.db`
2. Generates `genes_data.json`
3. Optionally creates standalone HTML

### Priority 2: Implement Placeholder Tracks
When data becomes available:
1. Neighborhood Conservation - needs BERDL pipeline update
2. Flux tracks - needs FBA results from modelseed
3. Phenotype/Fitness - needs integration with fitness.py

### Priority 3: Advanced Features
1. Clustering - implement k-means or hierarchical on selected tracks
2. Gene detail panel - click gene to show all annotations
3. Export - add PNG/SVG download buttons

### Priority 4: Integration
1. Move to KBDatalakeApps `/data/html/` structure
2. Add Vite build step if needed
3. Connect to `KBaseReport.create_extended_report()`

---

## Testing

### Manual Testing
1. Open `heatmap_standalone.html` in browser
2. Toggle tracks on/off with checkboxes
3. Click "Sort ↓" on various tracks
4. Adjust zoom slider
5. Hover over cells to see tooltips

### Verify Data Integrity
```python
import json
with open('genes_data.json') as f:
    data = json.load(f)
print(f"Gene count: {len(data)}")
print(f"Fields per gene: {len(data[0])}")
# Should show: 4617 genes, 21 fields
```

---

## Known Issues

1. **JupyterLab HTTP Server Access**: Direct HTTP server access may not work due to proxy configuration. Use standalone HTML or notebook inline display instead.

2. **Large File Size**: Standalone HTML is 706KB due to embedded data. Consider lazy loading for production.

3. **Consistency Score Interpretation**: Scores of -1 indicate missing data (rendered as gray). Valid scores range 0-1.

---

## Contact

- **Christopher Henry** - Requirements, data pipeline questions
- **Jose Faria** (jplfaria) - Development context
- **Boris** - Reference data deployment

---

*Generated by Claude Code, February 11, 2026*
