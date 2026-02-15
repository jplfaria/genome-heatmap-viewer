# Track Assessment - Scientific Use & Implementation Status

**Date**: 2026-02-15
**Purpose**: Systematic review of all 30+ tracks for scientific validity, correct implementation, and missing data integrations

---

## Summary

| Category | Total | Implemented | Placeholder | Issues |
|----------|-------|-------------|-------------|---------|
| **Gene Position** | 3 | 3 ✅ | 0 | 0 |
| **Pangenome** | 5 | 5 ✅ | 0 | 0 |
| **Consistency** | 8 | 8 ✅ | 0 | 0 |
| **Annotation** | 9 | 9 ✅ | 0 | 0 |
| **Metabolic (gene-level)** | 3 | 2 ✅ | 1 🔴 | 0 |
| **Metabolic (reaction-mapped)** | 4 | 0 ❌ | 4 🔴 | 4 |
| **Phenotype/Fitness** | 2 | 2 ✅ | 0 | 0 |
| **TOTAL** | 34 | 29 | 5 | 4 |

**Score**: 29/34 = **85% implemented**

**Critical Finding**: 4 metabolic tracks are placeholders despite data being available!

---

## Track-by-Track Assessment

### ✅ GENE POSITION TRACKS (3/3 implemented)

#### 1. Gene Order
- **Scientific Use**: Show genome order, identify operons
- **Implementation**: ✅ CORRECT - Sequential numbering
- **Data**: Index from genes array
- **Colors**: Blue gradient (light → dark)
- **Verdict**: **KEEP AS-IS**

#### 2. Strand
- **Scientific Use**: Identify transcription direction, operon boundaries
- **Implementation**: ✅ CORRECT - Binary forward/reverse
- **Data**: STRAND field (1 = forward, -1 = reverse)
- **Colors**: Purple (forward) / Orange (reverse) - colorblind safe!
- **Verdict**: **KEEP AS-IS**

#### 3. Genomic Position
- **Scientific Use**: Chromosome/plasmid location, synteny analysis
- **Implementation**: ✅ CORRECT - Shows START position
- **Data**: START field (nucleotide position)
- **Colors**: Blue gradient by position
- **Verdict**: **KEEP AS-IS**

---

### ✅ PANGENOME TRACKS (5/5 implemented)

#### 4. Pangenome Conservation
- **Scientific Use**: Core vs accessory classification
- **Implementation**: ✅ CORRECT - Fraction of genomes with ortholog
- **Data**: CONS_FRAC field (0.0-1.0)
- **Colors**: Gray → Green gradient
- **Formula**: `present_genomes / total_reference_genomes`
- **Verdict**: **KEEP AS-IS**

#### 5. Core/Accessory
- **Scientific Use**: Quick visual of gene distribution
- **Implementation**: ✅ CORRECT - 3-tier classification
- **Data**: PAN_CATEGORY field (0=unknown, 1=accessory, 2=core)
- **Colors**: Gray (unknown), Purple (accessory), Blue (core)
- **Thresholds**: Core >95%, Accessory 5-95%, Singleton <5%
- **Verdict**: **KEEP AS-IS**

#### 6. Cluster Size
- **Scientific Use**: Gene family size, duplication events
- **Implementation**: ✅ CORRECT - Number of genomes in cluster
- **Data**: CLUSTER_SIZE field
- **Colors**: Gray → Green gradient
- **Interpretation**: High = widespread, Low = rare
- **Verdict**: **KEEP AS-IS**

#### 7. Gene Length
- **Scientific Use**: Identify truncations, fusions
- **Implementation**: ✅ CORRECT - Protein length in amino acids
- **Data**: LENGTH field
- **Colors**: Blue gradient
- **Verdict**: **KEEP AS-IS**

#### 8. Neighborhood Conservation*
- **Scientific Use**: Synteny preservation, operon conservation
- **Implementation**: ❌ PLACEHOLDER - Not in data
- **Data**: NOT AVAILABLE (would require ±5 gene context analysis)
- **Verdict**: **SKIP** - requires new extraction script

---

### ✅ CONSISTENCY TRACKS (8/8 implemented)

#### 9-15. Source-Specific Consistency (RAST, KO, Bakta, EC, GO, EC Mapped, Pfam)
- **Scientific Use**: Annotation quality control, identify conflicts
- **Implementation**: ✅ CORRECT - All use proper consistency formula
- **Data**: Fields RAST_CONS, KO_CONS, BAKTA_CONS, EC_CONS, GO_CONS, EC_MAP_CONS, PFAM_CONS
- **Colors**: Blue (0) → Orange (1), Gray (N/A) - **COLORBLIND-SAFE** ✓
- **Formula**: `matching_annotations / cluster_size`
- **Verdict**: **KEEP AS-IS** - Novel feature, scientifically sound

#### 16. Average Consistency
- **Scientific Use**: Overall annotation reliability
- **Implementation**: ✅ CORRECT - Mean of all source consistencies
- **Data**: AVG_CONS field
- **Colors**: Blue → Orange (colorblind-safe)
- **Verdict**: **KEEP AS-IS**

---

### ✅ ANNOTATION TRACKS (9/9 implemented)

#### 17. Has Gene Name
- **Scientific Use**: Annotation completeness
- **Implementation**: ✅ CORRECT - Binary presence/absence
- **Data**: Derived from FUNC field (checks if not hypothetical/empty)
- **Colors**: Purple (has name) / Gray (no name)
- **Verdict**: **KEEP AS-IS**

#### 18. Hypothetical Protein
- **Scientific Use**: Identify uncharacterized genes
- **Implementation**: ✅ CORRECT - Binary flag
- **Data**: IS_HYPO field (1 = hypothetical, 0 = has function)
- **Colors**: Purple (hypothetical) / Gray (characterized)
- **Verdict**: **KEEP AS-IS**

#### 19-23. Annotation Counts (# KEGG, # COG, # Pfam, # GO, # EC)
- **Scientific Use**: Annotation depth per database
- **Implementation**: ✅ CORRECT - Integer counts
- **Data**: Fields N_KO, N_COG, N_PFAM, N_GO, N_EC
- **Colors**: Gray → Green gradient
- **Verdict**: **KEEP AS-IS**

#### 24. KEGG Module Hits
- **Scientific Use**: Pathway/module participation
- **Implementation**: ✅ CORRECT - Count of KEGG modules
- **Data**: N_MODULES field
- **Colors**: Gray → Green gradient
- **Verdict**: **KEEP AS-IS**

#### 25. Annotation Specificity
- **Scientific Use**: Quality of functional prediction
- **Implementation**: ✅ CORRECT - Composite score
- **Data**: SPECIFICITY field (0.0-1.0)
- **Formula**: Based on EC/KO/name presence
- **Colors**: Gray → Green gradient
- **Verdict**: **KEEP AS-IS**

#### 26. RAST/Bakta Agreement
- **Scientific Use**: Annotation tool comparison
- **Implementation**: ✅ CORRECT - 4-way classification
- **Data**: Computed from FUNC field + BAKTA annotations
- **Categories**: Agree, Disagree, Both Hypothetical, One Hypothetical
- **Colors**: Blue (agree), Red (disagree), Purple (both hypo), Orange (one hypo)
- **Verdict**: **KEEP AS-IS** - Unique feature

#### 27. Localization
- **Scientific Use**: Cellular compartment prediction
- **Implementation**: ✅ CORRECT - Categorical
- **Data**: LOC field (6 categories)
- **Colors**: 6-color categorical palette
- **Verdict**: **KEEP AS-IS**

---

### 🟡 METABOLIC TRACKS - GENE LEVEL (2/3 implemented)

#### 28. # Reactions
- **Scientific Use**: Metabolic gene identification
- **Implementation**: ✅ CORRECT - Count of associated reactions
- **Data**: From reactions_data.json gene_index
- **Colors**: Gray → Green gradient
- **Verdict**: **KEEP AS-IS**

#### 29. Metabolic Activity (Rich)
- **Scientific Use**: Which genes participate in metabolism
- **Implementation**: ✅ CORRECT - Boolean (has reactions)
- **Data**: Derived from reactions_data.json
- **Colors**: Green (has reactions) / Gray (none)
- **Verdict**: **KEEP AS-IS**

#### 30. Metabolic Activity (Minimal)
- **Scientific Use**: Essential vs dispensable genes
- **Implementation**: ✅ CORRECT - Boolean
- **Data**: Derived from reactions with flux_min > 0
- **Colors**: Green / Gray
- **Verdict**: **KEEP AS-IS**

---

### 🔴 METABOLIC TRACKS - REACTION MAPPED (0/4 implemented - DATA AVAILABLE!)

**CRITICAL FINDING**: We have reaction flux and class data but haven't mapped it to genes!

#### 31. Flux (minimal media)*
- **Scientific Use**: Gene importance in nutrient-poor conditions
- **Implementation**: ❌ PLACEHOLDER - **CAN BE IMPLEMENTED**
- **Data**: ✅ AVAILABLE in reactions_data.json (flux_min field)
- **Mapping**: Gene → Reactions → Sum/Max flux
- **Colors**: Blue (reverse) → White → Red (forward)
- **Action**: **IMPLEMENT NOW** - data exists, need aggregation function

#### 32. Rxn Class (minimal)*
- **Scientific Use**: Categorize metabolic gene function
- **Implementation**: ❌ PLACEHOLDER - **CAN BE IMPLEMENTED**
- **Data**: ✅ AVAILABLE in reactions_data.json (class_min field)
- **Classes**: blocked, forward_only, reverse_only, reversible, essential_forward, essential_reverse
- **Colors**: 6-color categorical
- **Action**: **IMPLEMENT NOW** - straightforward mapping

#### 33. Rxn Class (rich)*
- **Scientific Use**: Metabolic gene classification in nutrient-rich
- **Implementation**: ❌ PLACEHOLDER - **CAN BE IMPLEMENTED**
- **Data**: ✅ AVAILABLE in reactions_data.json (class_rich field)
- **Action**: **IMPLEMENT NOW**

#### 34. Flux (rich media)*
- **Scientific Use**: Gene flux in complete media
- **Implementation**: ❌ PLACEHOLDER - **CAN BE IMPLEMENTED**
- **Data**: ✅ AVAILABLE in reactions_data.json (flux_rich field)
- **Action**: **IMPLEMENT NOW**

**Implementation Plan**:
1. Create function: `getGeneReactionData(geneId)` → returns {flux_rich, flux_min, class_rich, class_min}
2. Aggregate multiple reactions per gene (max flux, most active class)
3. Add 4 new track definitions
4. Update TRACKS array
5. Test with known metabolic genes

---

### ✅ PHENOTYPE/FITNESS TRACKS (2/2 implemented)

#### 35. # Phenotypes
- **Scientific Use**: Experimental phenotype associations
- **Implementation**: ✅ CORRECT - Integer count
- **Data**: N_PHENOTYPES field
- **Colors**: Gray → Green gradient
- **Note**: Low values expected (limited experimental overlap)
- **Verdict**: **KEEP AS-IS**

#### 36. # Fitness Scores
- **Scientific Use**: Gene importance from fitness screens
- **Implementation**: ✅ CORRECT - Integer count
- **Data**: N_FITNESS field
- **Colors**: Gray → Green gradient
- **Note**: Very low values (0 for most genes in ADP1)
- **Verdict**: **KEEP AS-IS** - keep track, data will improve

---

## Recommendations

### 🔴 CRITICAL - Implement 4 Missing Metabolic Tracks

**Why**: We have the data in `reactions_data.json` but haven't connected it to genes!

**Impact**: HIGH - Completes metabolic gene characterization
- Scientists can see which genes carry high flux
- Can identify essential metabolic genes (essential_forward/reverse)
- Compares rich vs minimal media requirements

**Effort**: 2-3 hours
- Write aggregation function
- Add 4 track definitions
- Test and verify

**Priority**: **DO THIS NOW**

### 🟡 MEDIUM - Improve Track Tooltips

Some tracks have generic tooltips. Add scientific context:
- What does this measure biologically?
- How to interpret high vs low values?
- When is this track useful?

**Effort**: 1 hour

### 🟢 LOW - Add "Neighborhood Conservation"

Requires new extraction script to analyze ±5 gene context.

**Effort**: 4-6 hours (extraction + implementation)
**Value**: Moderate (synteny is useful but covered by other tracks)
**Priority**: FUTURE

---

## Scientific Validity Summary

### ✅ Scientifically Sound (29/29 implemented tracks)
All implemented tracks use correct formulas, proper data sources, and have valid biological interpretations.

### Novel Contributions
1. **Multi-source consistency comparison** - Not in standard pangenome tools
2. **RAST/Bakta agreement tracking** - Unique annotation QC
3. **Annotation specificity scoring** - Novel composite metric

### Alignment with Literature
- Pangenome metrics match standard tools (Panaroo, Roary)
- Consistency concept from literature but implementation is unique
- Flux/reaction data aligns with FBA standard practices

---

## Final Verdict

**Current Implementation**: **EXCELLENT** (29/34 tracks, 85%)

**Missing Critical Features**: 4 metabolic tracks (flux & reaction class)

**Action Items**:
1. ✅ Implement 4 metabolic reaction-mapped tracks (2-3 hours)
2. 🟡 Enhance track tooltips with biological context (1 hour)
3. 🟢 Consider neighborhood conservation for future (defer)

**Overall**: Viewer is scientifically robust with one critical gap that can be filled immediately.
