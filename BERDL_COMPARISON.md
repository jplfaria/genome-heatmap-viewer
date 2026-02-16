# BERDL Dashboard vs Our Genome Heatmap Viewer - Feature Comparison

Based on analysis of https://genomics.lbl.gov/~aparkin/KBase/berdl_output_ADP1.2.html (updated 2026-02-15)

## TOP KPI CARDS

### BERDL Has:
1. **GENOME ID** - Acinetobacter baylyi
2. **TOTAL GENES** - 3,235
3. **CORE** - 2,957 (91.4%)
4. **ACCESSORY** - 230 (7.1%)
5. **ANI RANGE** - 100.0% (1 pairwise comparison - Within species)
6. **MISSING CORE** - 94 pangenome clusters
7. **OUTLIER CATEGORIES** - 16 (15 enriched, 1 depleted)

### We Have:
- Organism name
- Genome ID
- Total genes
- Core genes
- Accessory genes
- Unknown (no cluster)
- Avg consistency
- Low consistency genes
- No cluster genes

### Missing / Should Add:
- ❌ **ANI RANGE** - Shows genomic similarity range to other genomes
- ❌ **MISSING CORE** - Count of pangenome core clusters this genome lacks
- ❌ **OUTLIER CATEGORIES** - Functional categories enriched/depleted vs pangenome

---

## TAB SECTIONS

### BERDL Has 11 Tabs:

#### 1. **Dendrogram** ✅ WE HAVE THIS
- UPGMA tree based on Jaccard distance
- Gene content similarity tree
- Shows shared gene clusters
- **We have this in our Tree tab**

#### 2. **Ribbon** ❌ MISSING
- Linear genome visualization
- Shows gene positions on chromosome
- Color-coded by function/category
- Useful for synteny analysis
- **This would be valuable to add**

#### 3. **Improbability** ❌ MISSING
- Statistical analysis of gene presence/absence patterns
- Identifies genes that are surprisingly present or absent
- Based on phylogenetic expectations
- **Interesting but complex to implement**

#### 4. **Gapfill** ❌ MISSING
- Shows gapfilled reactions in metabolic model
- Distinguishes model-inferred vs gene-supported reactions
- **We have gapfilling_status in reactions_data.json but don't visualize it**

#### 5. **Missing Core** ❌ MISSING
- List of core pangenome clusters absent from this genome
- Shows what "essential" genes are missing
- Helps identify genome incompleteness or genuine losses
- **We could compute this from our data**

#### 6. **KEGG Path** ❌ MISSING
- KEGG pathway coverage visualization
- Shows which metabolic pathways are complete vs incomplete
- Heatmap of pathway presence
- **We have the data (N_MODULES field) but no pathway-level view**

#### 7. **KEGG Module** ❌ MISSING
- KEGG module completeness
- More granular than pathways
- Shows which functional modules are complete
- **Could use N_MODULES data for this**

#### 8. **Metabolic Maps** ✅ WE HAVE THIS
- Escher metabolic pathway maps
- Color-coded reactions
- **We have this in our Metabolic Map tab**

#### 9. **PSORTb** ❌ MISSING
- Cellular localization predictions (PSORTb tool)
- Shows distribution of proteins across compartments
- Bar chart of localization categories
- **We have LOC field but no aggregate visualization**

#### 10. **Growth Pheno** ❌ MISSING
- Growth phenotype predictions
- Which carbon sources support growth
- Links to experimental data
- **We have phenotype data but don't visualize it well**

#### 11. **Essentiality** ❌ MISSING
- Essential gene predictions
- Based on metabolic modeling
- Shows which genes are required for growth
- **We have essential_forward/essential_reverse in flux classes**

---

## DETAILED FEATURES WE'RE MISSING

### HIGH PRIORITY - Easy to Implement

1. **Missing Core KPI Card**
   - Count pangenome core clusters not in user genome
   - Data: Already have pangenome_conservation_fraction
   - Computation: Count genes with cons_frac > 0.95 that user doesn't have
   - **Effort: 1 hour**

2. **Gapfill Status on Metabolic Map**
   - Show which reactions are gapfilled vs gene-supported
   - Data: We have `gapfilling_status` in reactions_data.json
   - Visual: Dashed border or different color for gapfilled reactions
   - **Effort: 1-2 hours**

3. **Localization Summary Chart**
   - Bar chart showing protein distribution across compartments
   - Data: We have LOC field for all genes
   - Add to Summary tab
   - **Effort: 2-3 hours**

4. **Pathway Completeness View**
   - Show KEGG pathway coverage
   - Data: We have N_MODULES field
   - Need to extract pathway → module → gene mappings
   - **Effort: 4-6 hours**

### MEDIUM PRIORITY - Moderate Effort

5. **Genome Ribbon View**
   - Linear visualization of chromosome
   - Color genes by function, pangenome status, etc.
   - Useful for synteny analysis
   - **Effort: 6-8 hours** (new visualization type)

6. **Growth Phenotype Predictions Table**
   - Show predicted carbon source utilization
   - Data: We have growth_phenotype_summary in database
   - Interactive table with filtering
   - **Effort: 4-6 hours**

7. **Essential Genes View**
   - List/visualization of essential genes
   - Data: We have essential_forward/reverse in flux classes
   - Could highlight on tracks or create dedicated view
   - **Effort: 3-4 hours**

### LOW PRIORITY - Complex or Low Value

8. **Improbability Analysis**
   - Requires phylogenetic modeling
   - Statistical analysis of gene gains/losses
   - **Effort: 10+ hours** (need new algorithms)

9. **Outlier Categories**
   - Functional enrichment analysis
   - Compare genome to pangenome background
   - Requires GO/COG enrichment testing
   - **Effort: 8-10 hours**

10. **ANI Range KPI**
    - Requires ANI calculations for all genome pairs
    - We only have ani_to_user for 1 genome
    - Would need to compute full ANI matrix
    - **Effort: 4-6 hours** (if we have the data)

---

## RECOMMENDATIONS

### IMMEDIATE (Do Today/Tomorrow):

1. ✅ **Add "Missing Core" KPI card** - Shows genome completeness
2. ✅ **Add "Contigs" stat bar on tree** - Already done! Assembly quality
3. ✅ **Show gapfill status on Metabolic Map** - Distinguish inferred reactions
4. ✅ **Add localization summary to Summary tab** - Protein compartment distribution

### SHORT TERM (This Week):

5. **Create KEGG Pathway coverage view**
   - Heatmap showing which pathways are complete
   - Use N_MODULES data we already have

6. **Improve Growth Phenotype display**
   - Currently just bars on tree (all identical)
   - Create table view with carbon source details

7. **Add Essential Genes filter/view**
   - Highlight essential metabolic genes
   - Use flux class data we already have

### LONG TERM (If Needed):

8. **Genome Ribbon view** - Nice for synteny but not critical
9. **Improbability analysis** - Interesting but complex
10. **Outlier categories** - Enrichment analysis

---

## VERDICT

**We're doing pretty well!** We already have:
- ✅ Tree/Dendrogram view
- ✅ Comprehensive tracks heatmap (they don't have this!)
- ✅ Metabolic maps
- ✅ Cluster analysis (they don't have this!)

**Critical gaps to fill:**
- Missing Core count (easy)
- Gapfill visualization (easy)
- Localization summary (easy)
- Pathway coverage (moderate)

**Our unique strengths:**
- Multi-source annotation consistency tracking (unique!)
- Interactive track selection and sorting (better than theirs!)
- Cluster embedding visualization (they don't have this!)
- Search and filtering (better than theirs!)

**Bottom line:** Fill the 4 easy gaps, and we'll be on par or better than BERDL for most use cases.
