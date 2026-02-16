#!/bin/bash
#
# Sync standalone genome heatmap viewer to KBase module
#
# Usage: ./sync-to-kbase.sh
#

set -e  # Exit on error

# Directories
STANDALONE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
KBASE_DIR="$HOME/repos/KBDatalakeDashboard/data/heatmap"

echo "════════════════════════════════════════════════════════════"
echo "  Syncing Genome Heatmap Viewer to KBase Module"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Source:      $STANDALONE_DIR"
echo "Destination: $KBASE_DIR"
echo ""

# Check if KBase repo exists
if [ ! -d "$HOME/repos/KBDatalakeDashboard" ]; then
    echo "❌ ERROR: KBDatalakeDashboard repository not found"
    echo "   Expected: $HOME/repos/KBDatalakeDashboard"
    echo ""
    echo "   Clone it first:"
    echo "   cd ~/repos && git clone git@github.com:jplfaria/KBDatalakeDashboard.git"
    exit 1
fi

# Create heatmap directory if doesn't exist
mkdir -p "$KBASE_DIR"

# Files/directories to EXCLUDE from sync
# (Data files, Python scripts, docs, git files)
EXCLUDES=(
    # Data files (KBase loads from API)
    "genes_data.json"
    "tree_data.json"
    "reactions_data.json"
    "summary_stats.json"
    "berdl_tables.db"
    "berdl_tables_ontology_terms.db"
    "metadata.json"

    # Python data generation scripts
    "generate_*.py"
    "extract_*.py"
    "add_*.py"

    # Documentation (keep in standalone only)
    "*.md"
    "CLAUDE.md"

    # Git and development files
    ".git"
    ".gitignore"
    ".claude"

    # Sync script itself
    "sync-to-kbase.sh"

    # Notebooks
    "*.ipynb"
)

# Build rsync exclude arguments
EXCLUDE_ARGS=""
for pattern in "${EXCLUDES[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude='$pattern'"
done

# Sync files
echo "📦 Syncing viewer files..."
eval rsync -av $EXCLUDE_ARGS "$STANDALONE_DIR/" "$KBASE_DIR/"

# Create VERSION file
if [ -d "$STANDALONE_DIR/.git" ]; then
    cd "$STANDALONE_DIR"
    VERSION=$(git describe --tags --always --dirty 2>/dev/null || echo "dev")
    COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    DATE=$(date +"%Y-%m-%d %H:%M:%S")

    cat > "$KBASE_DIR/VERSION" <<EOF
Genome Heatmap Viewer
Synced from: genome-heatmap-viewer
Version: $VERSION
Commit: $COMMIT
Date: $DATE
EOF
    echo "✓ Created VERSION file ($VERSION)"
else
    echo "⚠ No git repo found, skipping VERSION file"
fi

# Count synced files
SYNCED_COUNT=$(find "$KBASE_DIR" -type f | wc -l | tr -d ' ')

echo ""
echo "✓ Synced $SYNCED_COUNT files to KBase module"
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Next Steps"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "1. Review changes:"
echo "   cd ~/repos/KBDatalakeDashboard"
echo "   git diff data/heatmap/"
echo ""
echo "2. Rebuild module:"
echo "   make"
echo ""
echo "3. Test locally:"
echo "   kb-sdk test"
echo ""
echo "4. Commit and deploy:"
echo "   git add data/heatmap/"
echo "   git commit -m \"Sync heatmap viewer $VERSION\""
echo "   git push  # Auto-deploys to AppDev"
echo ""
echo "5. Test in AppDev:"
echo "   https://ci.kbase.us"
echo ""
