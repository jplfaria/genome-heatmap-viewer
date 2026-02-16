# Hardcoding Audit & Issues from Chris Feedback

## 🚨 CRITICAL HARDCODED VALUES TO FIX

### 1. **Reference Genome Count: "35" is hardcoded everywhere**
**Problem:** ADP1 has 13 reference genomes, not 35. E. coli had 35.

**Locations in index.html:**
- Line 1294: "how many of the 35 reference genomes" → should use `METADATA.n_ref_genomes`
- Line 1295: "present in all 35 reference genomes" → should use `METADATA.n_ref_genomes`
- Line 1303: "across 35 reference genomes" → should use `METADATA.n_ref_genomes`
- Line 1399: "across all 35 reference genomes" → should use `METADATA.n_ref_genomes`
- Line 1530: "all 35 reference genomes" → should use `METADATA.n_ref_genomes`
- Line 3235: `${(CONFIG && CONFIG.n_ref_genomes) || 35}` → **WRONG FALLBACK!** Should fail if missing
- Line 3257: `const nRef = (CONFIG && CONFIG.n_ref_genomes) || 35;` → **WRONG FALLBACK!**

**Fix:** Replace all "35" with `${METADATA.n_ref_genomes}` or variable

---

### 2. **Gene Count: "4617" hardcoded**
**Problem:** ADP1 has 3,235 genes, not 4,617 (E. coli count).

**Location:**
- Line 654: `<span id="position-info">0 - 4617 of 4617</span>`

**Fix:** Should be dynamically set from `genes.length` after data loads

---

## 🔧 REDUNDANT/CONFUSING UI ELEMENTS

### 3. **Protein Distribution Sidebar (Lines 597-602)**
**Problem:** There's a "Protein Distribution" section in the Tracks sidebar showing localization pie charts, BUT:
- There's already a "Subcellular Localization" **track** that visualizes the same data
- Chris wants a new **Distributions tab** that will make this even more redundant

**Feedback from Chris (r2.txt line 100-107):**
> "that protein distribution thing what would be really cool is if you had another tab... you could pick a track and it would show you that sort of distribution type information"

**Action:**
- ✅ **REMOVE** the Protein Distribution sidebar section entirely
- ✅ **CREATE** new Distributions tab where user selects ANY track to see distribution

---

### 4. **RAST/Bakta Agreement Track (Unreliable)**
**Problem:** Uses string matching to compare functions, not reliable.

**Feedback from Chris (r2.txt lines 182-188):**
> "between the function strings... which is another one that it's like... you're relying on ai to... it should i would remove i would just remove it or base it off of ec"

**Action:**
- ✅ **REMOVE** "RAST/Bakta Agreement" track entirely OR
- ⚠️ **REDESIGN** to use EC number comparison (if worth the effort)
- Line 1889 in index.html mentions this confusing behavior

---

### 5. **Hypothetical Search/Filter (Too Variable)**
**Problem:** Too many variations of "hypothetical" annotations.

**Feedback from Chris (r2.txt lines 141-145):**
> "hypothetical... there's too much variation... there's a lot of things that i'm not sure about... i think i should we should just remove the hypothetical stuff"

**Action:**
- ✅ **REMOVE** hypothetical-specific filtering
- ✅ **KEEP** IS_HYPO track (binary yes/no is fine)

---

## 📊 MISSING EXPLANATIONS (Legends & Tooltips)

### 6. **Cluster View Confusion**
**Problem:** Chris and Jose struggling to understand what cluster stats mean.

**Feedback from Chris (r2.txt lines 59-67, 129-138):**
> "cluster size looks weird... huge cluster sizes have thrown the color scale all out of whack"
> "missing core... clusters that have a pan genome label of core but they're not in each of the genomes"

**Actions Needed:**
- ✅ Add clear legend for cluster size coloring
- ✅ Explain cluster size = number of genomes containing that cluster
- ✅ Consider capping cluster size color scale at n_ref_genomes
- ✅ Add tooltip explaining Conservation vs Cluster Size vs Core/Accessory

---

### 7. **Fitness/Phenotype Data Source**
**Problem:** Not clear that this data is propagated from Adam's RBT database, not computed.

**Feedback from Chris (r2.txt lines 118-122):**
> "fitness scores... i would edit this and say these are propagated from like adam's rbt and seek database... this is the data for adp1 this is like propagated from the database"

**Action:**
- ✅ Update fitness/phenotype tooltips to explain data source
- ✅ Note this is ADP1-specific propagated data, not genome-wide computed

---

## 🎯 FEATURES TO ADD

### 8. **Distributions Tab** ⭐ HIGH PRIORITY
**Feedback from Chris (r2.txt lines 100-110):**
> "if you had another tab... you could pick a track and it would show you that sort of distribution type information... if it's a categorical track it would show you like a pie chart or a bar chart and if it was a numerical track it would show you like a histogram... that would be really useful"

**Design:**
- Tab next to "Tracks"
- Dropdown to select any track
- Automatically detect type (categorical → pie/bar, numerical → histogram)
- Shows distribution of gene counts per category/value
- Helps answer: "How many core vs accessory?" "What's the conservation distribution?"

---

### 9. **Missing Core Tree Stat**
**Feedback from Chris (r2.txt lines 130-137):**
> "Missing Core... clusters that have a pan genome label of core but they're not in each of the genomes... missing in the core that the genome doesn't have"

**Implementation:**
- In Tree tab, add stat for each genome: # of core clusters it's missing
- Requires: iterate cluster_data, find pan_category=Core, check if genome has it

---

### 10. **Reference Genome Data in Tree**
**Feedback from Chris (r2.txt lines 146-151, r3.txt lines 21-37):**
> "you have genome features and you have pan genome features and it's in pan genome features"
> "could we be able to get stuff for the other members... you have it for the other members"

**Problem:** Currently only showing user genome data. Need to pull data for all 13 (or N) reference genomes from `pan_genome_features` table in database.

**Action:**
- ✅ Extract pan_genome_features data (for all reference genomes)
- ✅ Show comparative stats in Tree view for each genome
- ✅ Enable better pangenome comparison visualization

---

## 🔥 KBASE-SPECIFIC ISSUES

### 11. **Module Name Mismatch (BLOCKING)**
**Error:** `Application module 'KBDatalakeDashboard2' must equal method module 'KBDatalakeDashboard'`

**Fix:**
```kidl
// In KBDatalakeDashboard.spec
module KBDatalakeDashboard2 {  // ← Change from KBDatalakeDashboard
    // ... rest unchanged
}
```

---

### 12. **Multi-Clade Support (CRITICAL)**
**Feedback from Chris (r3.txt lines 6-47):**
> "there is multiple pan genomes in it... you should have to pick what clade... so basically you should save multiple reports multiple pages one for each clade"

**GenomeDataLakeTables structure:**
```python
list<PangenomeData> pangenome_data;  // ARRAY - one per clade!

Each PangenomeData has:
  - pangenome_id (clade identifier)
  - list<genome_ref> user_genomes  (can be MULTIPLE!)
  - table_handle_ref sqllite_tables_handle_ref
```

**Implementation:**
1. Iterate over `pangenome_data` array
2. For each clade:
   - Download database from handle
   - Generate heatmap dashboard
   - Save as `clade_{pangenome_id}/index.html`
3. Create master `index.html` with table:
   - Columns: Clade Name, # Genomes, # User Genomes, Link
   - Clicking link opens that clade's dashboard

---

## 📝 SUMMARY OF ACTIONS

### IMMEDIATE (Standalone App)
1. ✅ Fix all hardcoded "35" → use `METADATA.n_ref_genomes`
2. ✅ Fix hardcoded "4617" in position-info → use `genes.length`
3. ✅ Remove "Protein Distribution" sidebar section
4. ✅ Remove "RAST/Bakta Agreement" track (or redesign with EC)
5. ✅ Remove hypothetical filtering options
6. ✅ Add Distributions tab (select track → see pie/bar/histogram)
7. ✅ Add cluster size legend/explanations
8. ✅ Update fitness/phenotype tooltips (explain RBT data source)
9. ✅ Add "Missing Core" stat to Tree tab

### MEDIUM PRIORITY
10. ✅ Extract pan_genome_features data for all reference genomes
11. ✅ Show reference genome stats in Tree view

### KBASE DEPLOYMENT
12. ✅ Fix `.spec` module name → `KBDatalakeDashboard2`
13. ✅ Test deployment with fixed name
14. ✅ Implement multi-clade support (index + per-clade dashboards)
15. ✅ Handle multiple user genomes per clade

---

## 🧠 UPDATE MEMORY WITH

```markdown
## Known Pitfalls - DO NOT HARDCODE

### Reference Genome Counts
- ❌ WRONG: Using "35" or any fixed number
- ✅ CORRECT: Always use `METADATA.n_ref_genomes` dynamically
- **Why it matters:** E. coli has 35 refs, ADP1 has 13, others vary widely

### Gene Counts
- ❌ WRONG: Using "4617" or any fixed number in UI
- ✅ CORRECT: Use `genes.length` after data loads
- Always update position-info dynamically

### Fallback Values in Code
- ❌ WRONG: `(CONFIG.n_ref_genomes) || 35` - fails silently with wrong value
- ✅ CORRECT: `METADATA.n_ref_genomes` - fail loud if missing, don't use fallback
```
