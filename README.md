# Genome Heatmap Viewer

A multi-track genome visualization tool for displaying genomic data as interactive heatmaps. Built for KBase/BERDL integration.

## Overview

This tool visualizes genes in a genome as a heatmap with multiple data "tracks" (bands). Each track represents a different type of data (gene length, conservation, annotation consistency, etc.) and is color-coded accordingly.

**Key Features:**
- Canvas-based rendering for 4,000+ genes
- 18 configurable data tracks (12 implemented, 6 placeholders)
- Sort by any track, toggle tracks on/off
- Zoom and pan through the genome
- Hover tooltips with gene details
- Standalone HTML or server-based viewing

## Quick Start

### Option 1: Open standalone HTML
Simply open `heatmap_standalone.html` in any web browser. This file contains embedded data and works offline.

### Option 2: Run with HTTP server
```bash
cd /path/to/genome-heatmap-viewer
python3 -m http.server 8889
# Open http://localhost:8889 in your browser
```

### Option 3: View in Jupyter
Open `view_heatmap.ipynb` in JupyterLab and run the cells to view inline.

## Files

| File | Description |
|------|-------------|
| `index.html` | Main viewer (requires HTTP server to load data) |
| `heatmap_standalone.html` | Self-contained version with embedded data |
| `genes_data.json` | Gene data for 4,617 genes (E. coli reference) |
| `view_heatmap.ipynb` | Jupyter notebook for inline viewing |
| `notebooks/` | Data extraction notebooks |
| `HEATMAP_VIEWER_REQUIREMENTS.md` | Detailed requirements from Christopher Henry |

## Data Tracks

### Currently Implemented

| Track | Type | Color Scheme |
|-------|------|--------------|
| Gene Order | Sequential | Blue → Red gradient |
| Gene Length | Sequential | Blue → Red gradient |
| Gene Direction | Binary | Green (+) / Red (-) |
| Pangenome Conservation Fraction | Sequential | Blue → Red gradient |
| Core/Accessory | Categorical | Gray/Orange/Green |
| Function Consensus (avg) | Consistency | Red → Yellow → Green |
| RAST Consistency | Consistency | Red → Yellow → Green |
| KO Consistency | Consistency | Red → Yellow → Green |
| GO Consistency | Consistency | Red → Yellow → Green |
| EC Consistency | Consistency | Red → Yellow → Green |
| Bakta Consistency | Consistency | Red → Yellow → Green |
| Annotation Specificity | Sequential | Blue → Red gradient |

### Placeholder Tracks (Data Not Yet Available)

- Neighborhood Conservation
- Flux (minimal media)
- Flux (rich media)
- Reaction Class (minimal)
- Phenotype Count
- Fitness Score Count

## Data Format

`genes_data.json` contains an array of gene arrays with these indices:

```javascript
[
  0: id,           // Integer - gene order
  1: fid,          // String - feature ID
  2: length,       // Integer - gene length in bp
  3: start,        // Integer - start position
  4: strand,       // String - "+" or "-"
  5: conservation, // Float - pangenome conservation fraction (0-1)
  6: pan_category, // Integer - 0=Unknown, 1=Accessory, 2=Core
  7: function,     // String - RAST function annotation
  8: n_ko,         // Integer - count of KEGG terms
  9: n_cog,        // Integer - count of COG terms
  10: n_pfam,      // Integer - count of Pfam terms
  11: n_go,        // Integer - count of GO terms
  12: localization,// String - PSORTb subcellular localization
  13: rast_cons,   // Float - RAST consistency score (-1 to 1)
  14: ko_cons,     // Float - KO consistency score (-1 to 1)
  15: go_cons,     // Float - GO consistency score (-1 to 1)
  16: ec_cons,     // Float - EC consistency score (-1 to 1)
  17: avg_cons,    // Float - Average consistency score (-1 to 1)
  18: bakta_cons,  // Float - Bakta consistency score (-1 to 1)
  19: ec_avg_cons, // Float - EC average consistency (EC + EC-mapped)
  20: specificity  // Float - Annotation specificity score (0-1)
]
```

## Data Source

Data is extracted from BERDL SQLite databases (`berdl_tables_ontology_terms.db`).

Key tables:
- `genome_features` - Gene positions, lengths, strands, annotations
- `pan_genome_features` - Pangenome cluster assignments
- `ontology_terms` - KO, COG, Pfam, GO term assignments

Consistency columns come from Christopher Henry's annotation comparison pipeline.

## Related Repositories

- **KBDatalakeApps**: https://github.com/kbaseapps/KBDatalakeApps
  - Contains the BERDL data pipeline and DataTables viewer
  - This heatmap viewer complements the existing tabular view

## Development

The viewer is pure HTML/CSS/JavaScript with no build step required. Edit `index.html` directly.

### Adding New Tracks

1. Add track definition to the `TRACKS` array in `index.html`
2. Update the data extraction query to include the new field
3. Regenerate `genes_data.json`
4. Update field index mapping if needed

### Color Schemes

Four color scheme types are defined:
- `sequential`: Blue → Red gradient for numeric ranges
- `binary`: Two distinct colors for boolean values
- `categorical`: Distinct colors for category values
- `consistency`: Red → Yellow → Green gradient for -1 to 1 range

## Requirements Origin

This project was specified by Christopher Henry (KBase) for genome-phenotype visualization. See `HEATMAP_VIEWER_REQUIREMENTS.md` for full details including:
- Original whiteboard sketches
- Quoted requirements
- Future feature roadmap
- Integration plans with KBase

## License

See KBase license terms.
