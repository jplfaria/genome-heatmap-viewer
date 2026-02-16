# KBase Integration - Sync Workflow Strategy

**Goal:** Keep standalone viewer as primary dev environment while syncing to KBase module
**Problem:** KBase SDK overhead makes rapid iteration slow
**Solution:** Develop standalone → Sync to KBase → Test → Deploy

---

## Core Principle: Standalone is Source of Truth

```
genome-heatmap-viewer/        ← PRIMARY (develop here)
    ├── index.html
    ├── genes_data.json
    └── config/

        ↓ SYNC SCRIPT ↓

KBDatalakeDashboard/          ← DEPLOYMENT (copy here)
    └── data/
        └── heatmap/
            ├── index.html
            ├── genes_data.json (template/example)
            └── config/
```

---

## Key Insight: Minimal Differences

The **only** difference between standalone and KBase versions should be **data loading**:

### Standalone Version
```javascript
// Load from local file
fetch('genes_data.json')
    .then(r => r.json())
    .then(genes => renderHeatmap(genes));
```

### KBase Version
```javascript
// Load from app-config.json + TableScanner API
fetch('../app-config.json')
    .then(r => r.json())
    .then(config => fetchGenesFromTableScanner(config.upa))
    .then(genes => renderHeatmap(genes));
```

**Everything else is identical:** rendering, tracks, UI, CSS, logic.

---

## Sync Workflow (Recommended)

### 1. Develop in Standalone

```bash
cd ~/repos/genome-heatmap-viewer

# Make changes
vim index.html

# Test locally (instant)
open index.html

# Commit when working
git add -A
git commit -m "Fix track rendering bug"
git push
```

**Benefits:**
- ✅ Instant feedback (no Docker build)
- ✅ Easy debugging (browser DevTools)
- ✅ Git history of all changes
- ✅ Can test with real data

### 2. Sync to KBase Module

Use a simple sync script:

```bash
# ~/repos/genome-heatmap-viewer/sync-to-kbase.sh
#!/bin/bash

STANDALONE_DIR=~/repos/genome-heatmap-viewer
KBASE_DIR=~/repos/KBDatalakeDashboard/data/heatmap

echo "Syncing standalone viewer to KBase module..."

# Create heatmap directory if doesn't exist
mkdir -p "$KBASE_DIR"

# Copy HTML/CSS/JS
rsync -av --exclude='genes_data.json' \
           --exclude='tree_data.json' \
           --exclude='reactions_data.json' \
           --exclude='summary_stats.json' \
           --exclude='berdl_tables.db' \
           --exclude='.git' \
           --exclude='*.md' \
           --exclude='generate_*.py' \
           --exclude='CLAUDE.md' \
           "$STANDALONE_DIR/" "$KBASE_DIR/"

echo "✓ Synced viewer files"
echo "✓ Skipped data files (KBase loads from API)"
echo ""
echo "Next steps:"
echo "  cd ~/repos/KBDatalakeDashboard"
echo "  git diff  # Review changes"
echo "  make      # Rebuild"
echo "  kb-sdk test  # Test"
```

**Usage:**
```bash
chmod +x sync-to-kbase.sh
./sync-to-kbase.sh
```

### 3. Adapt Data Loading (One-Time)

Create KBase-specific data loader in the synced `index.html`:

```javascript
// Add this to index.html (works in both contexts)
async function loadGenesData() {
    // Try KBase context first (app-config.json exists)
    try {
        const config = await fetch('../app-config.json').then(r => r.json());
        console.log('KBase context detected, loading from TableScanner API');
        return await fetchGenesFromTableScanner(config.upa);
    } catch (e) {
        // Fall back to standalone (local files)
        console.log('Standalone context, loading local data');
        return await fetch('genes_data.json').then(r => r.json());
    }
}
```

This way **same HTML works in both contexts**!

### 4. Test in KBase

```bash
cd ~/repos/KBDatalakeDashboard

# Review synced changes
git diff data/heatmap/

# If first time, modify KBDatalakeDashboardImpl.py
vim lib/KBDatalakeDashboard/KBDatalakeDashboardImpl.py

# Rebuild module
make

# Test locally
kb-sdk test

# Commit if tests pass
git add -A
git commit -m "Update heatmap viewer (synced from standalone)"
git push
```

### 5. Deploy to KBase

```bash
# Auto-deploys to AppDev on push
git push

# Wait 5-10 minutes for build
# Test in CI narrative: https://ci.kbase.us

# Promote to Next (staging)
kb-sdk release --beta

# Promote to Production
kb-sdk release
```

---

## File Organization

### Standalone Repo Structure

```
genome-heatmap-viewer/
├── index.html              ← Core viewer (syncs to KBase)
├── genes_data.json         ← Local test data (NOT synced)
├── tree_data.json          ← Local test data (NOT synced)
├── reactions_data.json     ← Local test data (NOT synced)
├── summary_stats.json      ← Local test data (NOT synced)
├── config/                 ← Config files (sync to KBase)
├── generate_*.py           ← Data extraction scripts (NOT synced)
├── sync-to-kbase.sh        ← Sync script (NOT synced)
├── *.md                    ← Documentation (NOT synced)
└── .claude/                ← Claude context (NOT synced)
```

### KBase Module Structure

```
KBDatalakeDashboard/
├── data/
│   ├── html/               ← Original dashboard (unchanged)
│   └── heatmap/            ← Our viewer (synced from standalone)
│       ├── index.html      ← Viewer (auto-detects KBase context)
│       ├── config/         ← Config files
│       └── genes_data.json ← OPTIONAL: Example/template only
└── lib/KBDatalakeDashboard/
    └── KBDatalakeDashboardImpl.py  ← Modified to include heatmap
```

---

## Handling Dependencies (Your Concern!)

### Escher Library

**Question:** Does KBase already have Escher?

**Answer:** Check KBDatalakeDashboard dependencies:

```bash
cd ~/repos/KBDatalakeDashboard
cat requirements.txt | grep -i escher
cat Dockerfile | grep -i escher
```

**If Escher is NOT in KBase:**

**Option 1: CDN (Recommended for viewer)**
```html
<!-- In index.html - works standalone AND in KBase -->
<script src="https://unpkg.com/escher@1.7.3/dist/escher.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/escher@1.7.3/dist/escher.min.css">
```

**Option 2: Add to KBase requirements**
```dockerfile
# In KBDatalakeDashboard/Dockerfile
RUN pip install escher==1.7.3
```

**Option 3: Bundle with viewer**
```bash
# Download Escher locally
cd ~/repos/genome-heatmap-viewer
mkdir -p vendor/escher
curl -o vendor/escher/escher.min.js https://unpkg.com/escher@1.7.3/dist/escher.min.js
curl -o vendor/escher/escher.min.css https://unpkg.com/escher@1.7.3/dist/escher.min.css

# Update index.html
<script src="vendor/escher/escher.min.js"></script>
```

**Recommendation:** Use CDN (Option 1) - simplest, no KBase modifications needed.

### Other Dependencies

**Pure JS libraries (no Python):**
- ✅ Just include in HTML (CDN or bundled)
- ✅ No KBase requirements.txt changes needed

**Python libraries (if needed):**
- Add to `KBDatalakeDashboard/requirements.txt`
- Rebuild Docker image

---

## Version Tracking

### Standalone Repo
```bash
# Track versions with git tags
git tag -a v1.0.0 -m "Initial KBase integration"
git push origin v1.0.0
```

### KBase Module
```bash
# Track which standalone version is synced
echo "v1.0.0" > data/heatmap/VERSION

# In commit messages
git commit -m "Sync heatmap viewer v1.0.0 from standalone"
```

### Version Display
```javascript
// In index.html
const VIEWER_VERSION = '1.0.0';
console.log(`Genome Heatmap Viewer v${VIEWER_VERSION}`);
```

---

## Bug Fix Workflow

### Example: Fix a track rendering bug

```bash
# 1. Fix in standalone (fast iteration)
cd ~/repos/genome-heatmap-viewer
vim index.html  # Fix bug
open index.html # Test immediately
git commit -am "Fix track rendering bug"

# 2. Sync to KBase
./sync-to-kbase.sh

# 3. Test in KBase
cd ~/repos/KBDatalakeDashboard
git diff data/heatmap/  # Verify sync
kb-sdk test            # Run tests
git commit -am "Sync heatmap viewer - fix track rendering"
git push               # Auto-deploy to AppDev

# 4. Test in AppDev narrative
# Open https://ci.kbase.us
# Run Build Genome Datalake Tables → Run Dashboard
# Verify fix

# 5. Promote if working
kb-sdk release --beta  # Next
kb-sdk release         # Production
```

**Time to test fix:**
- Standalone: **< 1 second** (refresh browser)
- KBase AppDev: **5-10 minutes** (Docker build + deploy)

This is why standalone-first is critical!

---

## Dealing with KBase-Specific Issues

### If issue only happens in KBase:

**Option 1: Reproduce standalone**
```javascript
// Simulate KBase environment in standalone
const MOCK_KBASE = true;

async function loadGenesData() {
    if (MOCK_KBASE) {
        // Simulate TableScanner API response
        return mockTableScannerData();
    }
    return fetch('genes_data.json').then(r => r.json());
}
```

**Option 2: Debug in KBase**
```javascript
// Add debug logging that survives to production
console.log('[DEBUG] Loading genes from TableScanner');
console.log('[DEBUG] UPA:', config.upa);
console.log('[DEBUG] Genes loaded:', genes.length);

// Check browser console in KBase narrative iframe
```

**Option 3: Use browser DevTools in KBase**
- Open KBase narrative
- Run dashboard app
- Right-click report iframe → Inspect
- Debug like normal web app

---

## Recommended Workflow Summary

### Daily Development
1. ✅ Work in `~/repos/genome-heatmap-viewer`
2. ✅ Test instantly in browser
3. ✅ Commit frequently
4. ✅ Push to GitHub (preserves standalone version)

### Sync to KBase (When Ready)
1. ✅ Run `./sync-to-kbase.sh`
2. ✅ Review `git diff` in KBDatalakeDashboard
3. ✅ Test with `kb-sdk test`
4. ✅ Commit and push (auto-deploys to AppDev)

### Test in KBase (Weekly)
1. ✅ Open AppDev narrative
2. ✅ Run Build Tables → Dashboard
3. ✅ Verify everything works
4. ✅ Promote to Next/Prod when stable

### Handle KBase-Specific Issues
1. ✅ Try to reproduce in standalone with mocks
2. ✅ If can't reproduce, debug in AppDev with DevTools
3. ✅ Fix in standalone if possible
4. ✅ Sync back to KBase

---

## Key Points

✅ **Standalone is source of truth** - develop here
✅ **Sync script automates copying** - one command
✅ **Same HTML works both places** - auto-detects context
✅ **Use CDN for Escher** - no KBase deps needed
✅ **Version tracking** - know what's deployed
✅ **Fast iteration** - test standalone instantly
✅ **KBase only for integration testing** - not daily dev

**NOT cumbersome** because:
- 90% of work in standalone (instant feedback)
- 10% in KBase (integration/deployment)
- Sync is one command
- Most bugs caught/fixed in standalone

---

## Next Step: Create Sync Script

Want me to create the actual `sync-to-kbase.sh` script with all the exclusions and safety checks?

