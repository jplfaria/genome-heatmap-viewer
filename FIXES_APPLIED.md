# Fixes Applied to Genome Heatmap Viewer

**Date:** 2026-02-16
**Context:** Comprehensive code audit during documentation writing revealed inconsistencies

---

## Critical Fix #1: Multi-Cluster Gene Consistency Handling

### Problem
266 genes (8.2% of dataset) belong to multiple pangenome clusters (semicolon-separated cluster IDs).

**Inconsistency:**
- **Conservation calculation** (Track 3): Used MAX conservation across all clusters ✅
- **Consistency calculation** (Tracks 5-10): Used FIRST cluster only ❌

This meant multi-cluster genes had underestimated consistency scores.

### Root Cause
`generate_genes_data.py` lines 396-400:
```python
# OLD CODE:
if cluster_ids:
    # For multi-cluster genes, use the first cluster
    cid = cluster_ids[0]  # ❌ Only uses first cluster
    ref_genes = cluster_ref_genes.get(cid, [])
    # ... compute consistency
```

### Fix Applied
Updated `generate_genes_data.py` lines 394-456 to loop through ALL clusters:

```python
# NEW CODE:
if cluster_ids:
    # For multi-cluster genes, compute for EACH cluster and take MAX
    all_rast_cons = []
    all_ko_cons = []
    all_go_cons = []
    all_ec_cons = []
    all_bakta_cons = []

    for cid in cluster_ids:  # ✅ Loop through ALL clusters
        ref_genes = cluster_ref_genes.get(cid, [])
        if not ref_genes:
            continue

        # Compute consistency for this cluster
        ref_rast = [g["rast_function"] for g in ref_genes if g["rast_function"]]
        if ref_rast:
            all_rast_cons.append(compute_consistency(rast_func, ref_rast))
        # ... same for KO, GO, EC, Bakta

    # Take MAX across all clusters ✅
    rast_cons = max(all_rast_cons) if all_rast_cons else -1
    ko_cons = max(all_ko_cons) if all_ko_cons else -1
    go_cons = max(all_go_cons) if all_go_cons else -1
    ec_cons = max(all_ec_cons) if all_ec_cons else -1
    bakta_cons = max(all_bakta_cons) if all_bakta_cons else -1
```

### Impact
- **266 genes** will now have potentially higher consistency scores
- Consistency tracks (RAST, KO, GO, EC, Bakta, Average) now consistent with conservation approach
- Per Chris Henry's guidance: "compute for both and take the higher one" ✅

### Files Modified
- `generate_genes_data.py` - lines 394-456

### Next Steps
- **Regenerate data:** Run `python generate_genes_data.py` to update `genes_data.json`
- **Verify:** Compare old vs new consistency scores for multi-cluster genes
- **Test:** Check that avg_cons track shows improved scores for affected genes

---

## Low Priority Fix #2: Remove EC_MAP_CONS from UMAP Embedding

### Problem
`EC_MAP_CONS` field always returns -1 (deprecated, not computed in current pipeline).

UMAP embedding in Cluster tab included this field as one of 23 features. Since it's always -1:
- `safe_float(-1)` converts to 0.0
- Entire column becomes constant (all zeros)
- During normalization, constant column stays 0
- Adds no information, just noise

### Fix Applied
Updated `generate_cluster_data.py` line 62:

```python
# OLD CODE (23 features):
feature_fields = [
    ("CONS_FRAC", 1.0),
    # ... other fields
    ("EC_MAP_CONS", 1.0),  # ❌ Always -1, adds noise
    # ... other fields
]

# NEW CODE (22 features):
feature_fields = [
    ("CONS_FRAC", 1.0),
    # ... other fields
    # EC_MAP_CONS removed - always -1 (deprecated field) ✅
    # ... other fields
]
```

### Impact
- UMAP now uses 22 meaningful features instead of 23
- Cleaner embedding, no constant columns
- Marginal improvement to dimensionality reduction quality

### Files Modified
- `generate_cluster_data.py` - line 62 (removed EC_MAP_CONS)

### Next Steps
- **Regenerate data:** Run `python generate_cluster_data.py` to update `cluster_data.json`
- **Visual check:** Verify Cluster tab UMAP still displays correctly
- **No breaking changes:** Only removed a constant column, embedding structure unchanged

---

## Documentation Corrections (No Code Changes Needed)

During the audit, I initially flagged these as issues, but code review revealed they were **documentation errors** on my part:

### ✅ Tree Stats Already Correct
- **My error:** Said tree stats mislabeled "Genes" (claimed it counted clusters)
- **Reality:** Code correctly computes AND displays both `n_genes` and `n_clusters` separately
- **No fix needed** - code was already correct

### ✅ Missing Core Computation Already Fixed
- **My error:** Said missing core logic was backwards
- **Reality:** Old buggy code already commented out, Tree tab shows correct "Core %" stat
- **No fix needed** - code was already correct

### ✅ EC_MAP_CONS Track Acceptable As-Is
- **Status:** Non-functional (always -1) but disabled by default
- **Decision:** Keep as placeholder track, acceptable for now
- **No fix needed** - acceptable as-is

---

## Remaining Low Priority Issues (Deferred)

These issues were identified but not fixed (low impact, can be addressed later):

1. **Cluster tab N/A handling:** -1 values converted to 0.0 instead of NaN (acceptable workaround)
2. **Metabolic map gene matching:** Regex-based locus tag extraction may miss edge cases (works for standard cases)
3. **Distributions tab UX:** No outlier handling, fixed bin count, no export (nice-to-haves)

---

## Summary

**Total issues found:** 9 (1 critical, 3 moderate, 5 low)
**Issues fixed:** 2 (1 critical, 1 low)
**Documentation errors:** 3 (code was already correct)
**Issues deferred:** 3 (all low priority)

**Most important fix:** Multi-cluster gene consistency now uses MAX across all clusters, affecting 266 genes (8.2% of dataset) - ensures consistency with conservation calculation approach.

---

## Testing Checklist

Before deploying to KBase:

- [ ] Run `python generate_genes_data.py` to regenerate genes_data.json with fixed consistency
- [ ] Run `python generate_cluster_data.py` to regenerate cluster_data.json with 22 features
- [ ] Visual check: Load app, verify all tracks display correctly
- [ ] Spot check: Sample 5 multi-cluster genes, verify consistency scores increased (or stayed same)
- [ ] Playwright tests: Run existing test suite, all should pass
- [ ] Compare: Old vs new avg_cons distribution (expect slight rightward shift)

---

## Files Modified

1. `generate_genes_data.py` - Multi-cluster consistency fix (lines 394-456)
2. `generate_cluster_data.py` - Remove EC_MAP_CONS from UMAP (line 62)
3. `TRACK_DOCUMENTATION.md` - Comprehensive documentation + fixes section
4. `FIXES_APPLIED.md` - This file
