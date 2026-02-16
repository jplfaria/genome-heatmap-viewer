# Comprehensive Track and Tab Check

## CRITICAL ISSUES FOUND

### 1. **N_FITNESS Track - ALL ZEROS** ❌
- **Track**: # Fitness Scores (field 37)
- **Problem**: Every gene has value 0 (3,235/3,235 genes)
- **Impact**: Track shows solid blue bar, completely useless
- **Root cause**: Data extraction script `generate_genes_data.py` is not populating this field

### 2. **N_PHENOTYPES Track - HAS DATA** ✅
- **Track**: # Phenotypes (field 36)
- **Status**: 2,297 genes with non-zero values (0-230 range)
- **Looks correct**

### 3. **ESSENTIALITY Track - HAS DATA** ✅
- **Track**: Gene Essentiality (field 35)
- **Status**: 2,069 genes with non-zero values (-1 to 1.0 range)
- **Looks correct**

---

## Systematic Track Check (In Progress)

Checking all 30 data tracks + 6 tabs...

### Tracks Tab
- [ ] Gene Order (ID)
- [ ] Gene Direction (STRAND)
- [ ] Pangenome Conservation (CONS_FRAC)
- [ ] Core/Accessory (PAN_CAT)
- [ ] Function Consensus avg (AVG_CONS)
- [ ] RAST Consistency (RAST_CONS)
- [ ] KO Consistency (KO_CONS)
- [ ] GO Consistency (GO_CONS)
- [ ] EC Consistency (EC_CONS)
- [ ] Bakta Consistency (BAKTA_CONS)
- [ ] Annotation Specificity (SPECIFICITY)
- [ ] # KEGG Terms (N_KO)
- [ ] # COG Terms (N_COG)
- [ ] # Pfam Terms (N_PFAM)
- [ ] # GO Terms (N_GO)
- [ ] Subcellular Localization (LOC)
- [ ] Has Gene Name (HAS_NAME)
- [ ] # EC Numbers (N_EC)
- [ ] Cluster Size (CLUSTER_SIZE)
- [ ] KEGG Module Hits (N_MODULES)
- [ ] EC Mapped Consistency (EC_MAP_CONS)
- [ ] Protein Length (PROT_LEN)
- [ ] Flux rich media (RICH_FLUX)
- [ ] Flux minimal media (MIN_FLUX)
- [ ] Rxn Class rich (RICH_CLASS)
- [ ] Rxn Class minimal (MIN_CLASS)
- [ ] Gene Essentiality (ESSENTIALITY) ✅
- [ ] # Phenotypes (N_PHENOTYPES) ✅
- [ ] # Fitness Scores (N_FITNESS) ❌ ALL ZEROS

### Distributions Tab
- [ ] Check each track's distribution
- [ ] Verify statistics (mean, median, count)
- [ ] Check for empty/silly distributions

### Tree Tab
- [ ] UPGMA tree renders
- [ ] Stats are correct (n_genes, n_clusters)
- [ ] Genome labels correct

### Cluster Tab
- [ ] UMAP renders
- [ ] Gene Features embedding works
- [ ] Presence-Absence embedding works
- [ ] All color-by options work

### Metabolic Map Tab
- [ ] Global map loads
- [ ] Core map loads
- [ ] All 6 color modes work
- [ ] Gene links work

### Help Tab
- [ ] All text accurate
- [ ] Color examples match
- [ ] No errors

---

## DATA STATISTICS

### Phenotype/Fitness Fields
```
N_FITNESS (field 37):     0 genes with data (0/3235)  ❌ BROKEN
N_PHENOTYPES (field 36):  2297 genes with data (71%)  ✅
ESSENTIALITY (field 35):  2069 genes with data (64%)  ✅
```

---

## NEXT ACTIONS

1. Fix generate_genes_data.py to populate N_FITNESS field
2. Check every other track systematically using browser
3. Check all distributions
4. Document all issues found
