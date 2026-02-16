# Comprehensive Action Plan

## Phase 0: FIX KBASE BLOCKER (5 min) 🔥

**Status:** CRITICAL - App won't run until fixed

1. Update `.spec` file module name
2. Commit + push to upstream
3. Re-register in Catalog
4. Verify deployment

---

## Phase 1: FIX HARDCODED VALUES (30 min) ⚡

**Goal:** Make app work correctly for ANY genome, not just E. coli

### Fix #1: Reference Genome Count (10 lines to change)
- [ ] Search index.html for all "35" occurrences
- [ ] Replace with `${METADATA.n_ref_genomes}` in templates
- [ ] Replace with `METADATA.n_ref_genomes` in JS variables
- [ ] Remove bad fallback: `|| 35` → should fail if missing

### Fix #2: Gene Count
- [ ] Find `<span id="position-info">` initialization
- [ ] Change from hardcoded to dynamic update after data loads

### Fix #3: Test with ADP1 data
- [ ] Verify all counts show "13 reference genomes"
- [ ] Verify position shows "0 - 3235 of 3235"

**Time: 30 min**

---

## Phase 2: REMOVE REDUNDANT/CONFUSING FEATURES (45 min) 🗑️

### Remove #1: Protein Distribution Sidebar
- [ ] Find sidebar section (lines ~597-602)
- [ ] Delete entire section
- [ ] Test that localization track still works
- [ ] Verify no JS errors

### Remove #2: RAST/Bakta Agreement Track
- [ ] Remove from config.json tracks array
- [ ] Remove from cluster_color_options
- [ ] Remove from analysis_views
- [ ] Search for "agreement" in index.html, clean up references
- [ ] Remove AGREEMENT field explanation text

### Remove #3: Hypothetical Search Options
- [ ] Find hypothetical-specific filtering in search/filter UI
- [ ] Remove (but keep IS_HYPO track - that's fine)
- [ ] Clean up related tooltips

**Time: 45 min**

---

## Phase 3: ADD EXPLANATIONS & CLARITY (30 min) 📝

### Improve #1: Cluster View Tooltips
- [ ] Add explanation: "Cluster Size = number of genomes with this cluster"
- [ ] Explain difference: Conservation (fraction) vs Cluster Size (absolute count)
- [ ] Add note about why huge clusters throw off color scale
- [ ] Consider capping cluster size scale at n_ref_genomes

### Improve #2: Fitness/Phenotype Data Source
- [ ] Update N_FITNESS tooltip: "Propagated from Adam's RBT database for ADP1"
- [ ] Update ESSENTIALITY tooltip: same
- [ ] Update N_PHENOTYPES tooltip: same
- [ ] Add caveat: "ADP1-specific data, not genome-wide"

**Time: 30 min**

---

## Phase 4: ADD DISTRIBUTIONS TAB (2-3 hours) 🎯

**Design:**
```
┌─────────────────────────────────┐
│ Tracks │ Tree │ Distributions   │
├─────────────────────────────────┤
│ SELECT TRACK:                   │
│ [Pangenome Conservation    ▼]   │
│                                 │
│ ┌─────────────────────────────┐ │
│ │   📊 Histogram              │ │
│ │   ┌─┐                       │ │
│ │   │█│  ┌─┐                  │ │
│ │   │█│  │█│  ┌─┐             │ │
│ │   └─┘  └─┘  └─┘             │ │
│ │  0.0  0.5  1.0              │ │
│ │                             │ │
│ │  Total: 3235 genes          │ │
│ │  Mean: 0.72                 │ │
│ │  Median: 0.81               │ │
│ └─────────────────────────────┘ │
└─────────────────────────────────┘
```

### Implementation Steps:
1. [ ] Add "Distributions" tab button in HTML
2. [ ] Create distributions container/sidebar
3. [ ] Add track selector dropdown (populate from TRACKS)
4. [ ] Detect track type (categorical vs sequential vs consistency)
5. [ ] Implement categorical → pie chart + bar chart
6. [ ] Implement sequential → histogram with bins
7. [ ] Implement consistency → histogram (handle -1 = N/A separately)
8. [ ] Add summary stats (count, mean, median for numerical)
9. [ ] Style to match other tabs
10. [ ] Test with all track types

**Time: 2-3 hours**

---

## Phase 5: ADD MISSING CORE STAT (1 hour) 📊

**Goal:** Show which core genes each genome is missing

### Implementation:
1. [ ] In Tree tab, add "Missing Core" stat
2. [ ] Load cluster_data.json
3. [ ] For each genome in tree:
   - Filter clusters where `pan_category === 'Core'`
   - Check if genome has genes in that cluster
   - Count how many core clusters are absent
4. [ ] Display as tree stat
5. [ ] Add tooltip explaining what this means

**Time: 1 hour**

---

## Phase 6: EXTRACT REFERENCE GENOME DATA (2-3 hours) 🔬

**Goal:** Show data for all 13 reference genomes in Tree, not just user genome

### Database Work (Python):
1. [ ] Create `extract_pan_genome_features.py`
2. [ ] Query `pan_genome_features` table for ALL genomes
3. [ ] Extract key stats per genome:
   - Total genes
   - Core gene count
   - Accessory gene count
   - Average conservation
   - Missing core genes
4. [ ] Output `ref_genomes_data.json`

### Viewer Integration:
5. [ ] Add ref_genomes_data to config.json
6. [ ] Load in viewer
7. [ ] Display in Tree tab for each genome node
8. [ ] Enable comparison view

**Time: 2-3 hours**

---

## Phase 7: SYNC TO KBASE & TEST (1 hour) 🚀

1. [ ] Run `./sync-to-kbase.sh`
2. [ ] Review changes in KBDatalakeDashboard
3. [ ] Commit
4. [ ] Push upstream
5. [ ] Re-register
6. [ ] Test in AppDev with Philippe's database
7. [ ] Fix any KBase-specific issues

**Time: 1 hour**

---

## Phase 8: MULTI-CLADE SUPPORT (4-6 hours) 🌳

**This is REQUIRED for production but can come after initial testing**

### Design:
```
Master index.html:
┌───────────────────────────────────────┐
│ Genome Datalake Dashboard             │
├───────┬─────────┬───────────┬─────────┤
│ Clade │ Genomes │ User Gen. │ View    │
├───────┼─────────┼───────────┼─────────┤
│ E.coli│   35    │     1     │ [Open]  │
│ Acine.│   13    │     2     │ [Open]  │
│ Staph.│   42    │     1     │ [Open]  │
└───────┴─────────┴───────────┴─────────┘
```

### Implementation:
1. [ ] Modify KBDatalakeDashboardImpl.py:
   - Iterate over `pangenome_data` array
   - For each clade:
     - Download database from handle via DataFileUtil
     - Generate dashboard in `clade_{pangenome_id}/` subdirectory
     - Create per-clade `app-config.json`
2. [ ] Create master `index.html` template with table
3. [ ] Update kbase-data-loader.js to handle clade-specific paths
4. [ ] Test with multi-clade dataset

**Time: 4-6 hours**

---

## TOTAL TIME ESTIMATE

- Phase 0 (KBase blocker): 5 min ✅ DO FIRST
- Phase 1 (Hardcoding fixes): 30 min ⚡ DO SECOND
- Phase 2 (Remove junk): 45 min
- Phase 3 (Add explanations): 30 min
- Phase 4 (Distributions tab): 2-3 hours ⭐
- Phase 5 (Missing Core): 1 hour
- Phase 6 (Ref genome data): 2-3 hours
- Phase 7 (KBase sync & test): 1 hour
- Phase 8 (Multi-clade): 4-6 hours (can defer)

**Total: 8-12 hours of work**

**Suggested approach:**
- Phases 0-3: ~2 hours → Quick wins, app works correctly
- Phase 4: ~3 hours → Major feature add
- Phases 5-6: ~4 hours → Data enrichment
- Phase 7: ~1 hour → KBase deployment
- Phase 8: Later (after successful testing)

---

## SUCCESS CRITERIA

### For Standalone:
- ✅ All counts are dynamic (no hardcoded 35, 4617)
- ✅ Redundant features removed
- ✅ Clear explanations for all stats
- ✅ Distributions tab working
- ✅ Missing Core stat in Tree
- ✅ Works with both E. coli and ADP1 data

### For KBase:
- ✅ Module name fixed, app runs
- ✅ Loads from TableScanner correctly
- ✅ Works with Philippe's database
- ✅ Multi-clade support (can defer to v2)

---

## START HERE:

**Next command:** Fix KBase module name blocker (5 min)
