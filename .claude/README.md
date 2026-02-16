# Claude Code Project Configuration

This directory contains Claude Code project-specific configuration and context.

## Memory System

**Location:** `memory/`

Claude Code's auto memory system preserves knowledge across conversations:

- **`MEMORY.md`** - Main project memory (auto-loaded, 200 line limit)
  - Current project status and phase completion
  - Key architecture and data schema
  - Critical issues and workarounds
  - Stakeholder information

- **`kbase-sdk.md`** - KB SDK development reference
  - Auto-generated vs manual files
  - KIDL patterns and templates
  - Python implementation patterns
  - UI configuration examples
  - Deployment workflow
  - Integration strategy for heatmap

## KBase SDK Context

**Location:** `kbase-context/`

Reference documentation from Chris Henry's ClaudeCommands:

- **`kidl-reference.md`** - KIDL (KBase Interface Definition Language) syntax
- **`ui-spec-reference.md`** - Narrative UI specification patterns
- **`kbutillib-integration.md`** - KBUtilLib utility library usage
- **`workspace-datatypes.md`** - KBase workspace data type system

These files provide context for KB SDK development without cluttering memory.

## Project Documentation

**Location:** `~/repos/genome-heatmap-viewer/` (root)

Comprehensive analysis documents:

- **`KBASE_SDK_DEVELOPMENT_GUIDE.md`** - Complete KB SDK reference (24KB)
  - Module structure and lifecycle
  - KIDL specification language
  - Python implementation patterns
  - UI configuration system
  - Testing and deployment
  - Integration strategy

- **`KBASE_DASHBOARD_ANALYSIS.md`** - KBDatalakeDashboard deep dive
  - Architecture and data flow
  - Frontend technology stack
  - Integration points
  - Recommended integration approach

- **`KBASE_APPS_ANALYSIS.md`** - KBDatalakeApps pipeline analysis
  - Data generation workflow
  - SQLite schema
  - BERDL integration
  - Missing pangenome analysis

- **`COMPLETE_FEATURE_IMPLEMENTATION.md`** - BERDL parity completion
- **`BERDL_COMPARISON.md`** - Feature comparison
- **`SUMMARY_TAB_REMOVAL.md`** - UI streamlining work

## How Memory Works

When context compacts (conversation gets too long), Claude Code:

1. Summarizes the conversation into a compact history
2. **Preserves `memory/` files** - these are ALWAYS loaded
3. Forgets specific conversation details

To preserve knowledge:
- ✅ Add critical patterns to `memory/kbase-sdk.md`
- ✅ Add project decisions to `memory/MEMORY.md`
- ❌ Don't rely on conversation history
- ❌ Don't assume I remember previous sessions without memory files

## Usage in Future Sessions

When starting a new session:
1. Memory files auto-load (no action needed)
2. Reference `kbase-context/*.md` for KB SDK patterns
3. Reference root `*.md` docs for deep dives
4. Use `memory/kbase-sdk.md` for quick copy-paste templates

## Updating Memory

If you need to preserve new knowledge:

```bash
# Edit memory files directly
vim ~/.claude/projects/-Users-jplfaria-repos-genome-heatmap-viewer/memory/MEMORY.md
vim ~/.claude/projects/-Users-jplfaria-repos-genome-heatmap-viewer/memory/kbase-sdk.md

# Or ask Claude to update them during the session
```

Keep `MEMORY.md` under 200 lines to avoid truncation!

