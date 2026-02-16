# KBase SDK Development - Complete Assessment

**Date:** 2026-02-16
**Purpose:** Comprehensive understanding of KB SDK development workflow for integrating genome heatmap viewer

---

## Executive Summary

The **KBase SDK** is a Docker-based framework for creating bioinformatics apps that run in KBase Narratives. It uses a specification-driven approach where you define interfaces in KIDL (KBase Interface Definition Language), implement methods in Python, and configure UIs through JSON/YAML files. The SDK auto-generates server code, handles authentication, manages workspace operations, and provides testing infrastructure.

**Key Insight:** KB SDK development is highly automated - you write minimal code (KIDL spec, Python impl, UI config) and the SDK generates everything else (server, clients, deployment scripts, Docker config).

---

## 1. Core Concepts

### What is the KB SDK?

A toolset for creating KBase apps that can be:
- **Dynamically registered** - No KBase core team involvement needed
- **Deployed in minutes** - Docker-based containerization
- **Run in narratives** - Interactive computational notebooks
- **Tracked and cited** - Usage metrics and DOI citations

### Problem It Solves

Most bioinformatics tools exist as standalone CLIs. KB SDK wraps them to provide:
- Cloud computing resources (no local installation)
- Data provenance tracking
- Reproducible computational workflows
- Community sharing and discovery
- Automatic versioning and updates

---

## 2. KB SDK Module Structure

### Directory Layout

```
MyModule/
├── kbase.yml                    # Module metadata (MUST EDIT)
├── MyModule.spec                # KIDL interface definition (MUST EDIT)
├── Makefile                     # Build automation (auto-generated)
├── Dockerfile                   # Container config (MAY EDIT for dependencies)
├── deploy.cfg                   # Deployment settings
├── dependencies.json            # SDK module dependencies (MAY EDIT)
├── requirements.txt             # Python packages (MAY EDIT)
├── requirements_kbase.txt       # KBase-specific Python (rarely edit)
├── lib/
│   └── MyModule/
│       ├── MyModuleImpl.py      # Python implementation (MUST EDIT)
│       ├── MyModuleServer.py    # Auto-generated - DO NOT EDIT
│       └── __init__.py
├── ui/
│   └── narrative/
│       └── methods/
│           └── my_method/
│               ├── spec.json     # UI parameter mapping (MUST EDIT)
│               └── display.yaml  # UI labels/docs (MUST EDIT)
├── data/                        # Reference data, HTML assets
├── scripts/
│   └── entrypoint.sh            # Container entry point
├── test/
│   └── MyModule_server_test.py  # Unit tests (SHOULD EDIT)
└── biokbase/                    # KBase auth/logging utilities
```

### Files You Edit

**Required:**
1. `kbase.yml` - Module name, description, owners
2. `MyModule.spec` - KIDL function definitions
3. `lib/MyModule/MyModuleImpl.py` - Python implementation
4. `ui/narrative/methods/*/spec.json` - UI parameter config
5. `ui/narrative/methods/*/display.yaml` - UI documentation

**Optional:**
6. `Dockerfile` - Add system dependencies
7. `requirements.txt` - Add Python packages
8. `dependencies.json` - Add other KB SDK modules
9. `data/` - Add reference data or HTML files

**Never Edit:**
- `lib/MyModule/MyModuleServer.py` (regenerated on `make`)
- Auto-generated client code

---

## 3. KIDL (KBase Interface Definition Language)

### Purpose

KIDL is a specification language that defines:
- Data types (structures, primitives, collections)
- Function signatures (inputs, outputs)
- Authentication requirements
- API documentation

### Basic Syntax

```kidl
/*
Module documentation
*/
module MyModule {

    /* Type definitions */
    typedef string genome_ref;

    typedef structure {
        string workspace_name;
        string input_ref;
        int optional_param;
    } MyInputParams;

    typedef structure {
        string report_name;
        string report_ref;
    } ReportResults;

    /* Function definition */
    funcdef my_method(MyInputParams params)
        returns (ReportResults output)
        authentication required;
};
```

### Primitive Types

- `string` - Text
- `int` - Integer
- `float` - Floating point
- `bool` - Boolean
- `UnspecifiedObject` - JSON object

### Collection Types

- `list<T>` - Ordered array
- `mapping<K, V>` - Key-value dict
- `tuple<T1, T2, ...>` - Fixed-size ordered values

### Best Practices

✅ **DO:**
- Use descriptive names (`genome_ref` not `gr`)
- Document everything with `/* comments */`
- Use structures for parameters (easier to extend)
- Use `mapping<string, Feature>` for ID lookups
- Use `list<Feature>` for ordered collections

❌ **DON'T:**
- Create deeply nested structures (keep flat)
- Use abbreviations
- Skip documentation (becomes API docs)
- Create redundant fields instead of collections

### Authentication Modes

```kidl
funcdef public_method(...) authentication none;
funcdef optional_auth(...) authentication optional;
funcdef required_auth(...) authentication required;
```

---

## 4. Python Implementation

### Implementation Class

After `make`, SDK generates `MyModuleImpl.py` with:

```python
class MyModule:
    def __init__(self, config):
        self.callback_url = os.environ['SDK_CALLBACK_URL']
        self.scratch = config['scratch']
        self.shared_folder = config['scratch']
        # Initialize service clients
        self.dfu = DataFileUtil(self.callback_url)
        self.kr = KBaseReport(self.callback_url)

    def my_method(self, ctx, params):
        """
        Implementation of my_method
        :param params: MyInputParams structure
        :returns: ReportResults structure
        """
        # Validate parameters
        self._validate_params(params)

        # Do work
        results = self._do_analysis(params)

        # Generate report
        report = self._create_report(results, params['workspace_name'])

        return {
            'report_name': report['name'],
            'report_ref': report['ref']
        }
```

### Service Clients

Common clients initialized in `__init__`:

```python
from installed_clients.DataFileUtilClient import DataFileUtil
from installed_clients.KBaseReportClient import KBaseReport
from installed_clients.WorkspaceClient import Workspace

self.dfu = DataFileUtil(callback_url)  # File operations
self.kr = KBaseReport(callback_url)    # Report generation
self.ws = Workspace(workspace_url)     # Workspace operations
```

### Common Patterns

**1. Workspace Object Retrieval:**
```python
obj = self.ws.get_objects2({
    'objects': [{'ref': params['input_ref']}]
})['data'][0]
data = obj['data']
info = obj['info']
```

**2. File Upload to Shock:**
```python
shock_id = self.dfu.file_to_shock({
    'file_path': html_dir,
    'make_handle': 0,
    'pack': 'zip'
})['shock_id']
```

**3. Report Creation:**
```python
report_info = self.kr.create_extended_report({
    'direct_html_link_index': 0,
    'html_links': [{
        'shock_id': shock_id,
        'name': 'index.html',
        'label': 'Dashboard'
    }],
    'report_object_name': 'my_report_' + str(uuid.uuid4()),
    'workspace_name': workspace_name
})
```

---

## 5. UI Configuration

### spec.json - Parameter Mapping

```json
{
    "ver": "0.0.1",
    "authors": ["username"],
    "contact": "https://kbase.us/contact-us/",
    "categories": ["active"],
    "widgets": {
        "input": null,
        "output": "no-display"
    },
    "parameters": [
        {
            "id": "input_ref",
            "optional": false,
            "advanced": false,
            "allow_multiple": false,
            "field_type": "text",
            "text_options": {
                "valid_ws_types": ["KBaseFBA.GenomeDataLakeTables"]
            }
        }
    ],
    "behavior": {
        "service-mapping": {
            "name": "MyModule",
            "method": "my_method",
            "input_mapping": [
                {
                    "narrative_system_variable": "workspace",
                    "target_property": "workspace_name"
                },
                {
                    "input_parameter": "input_ref",
                    "target_property": "input_ref",
                    "target_type_transform": "resolved-ref"
                }
            ],
            "output_mapping": [
                {
                    "service_method_output_path": [0, "report_name"],
                    "target_property": "report_name"
                },
                {
                    "service_method_output_path": [0, "report_ref"],
                    "target_property": "report_ref"
                }
            ]
        }
    }
}
```

### display.yaml - UI Documentation

```yaml
name: My Method Name
tooltip: Short description shown on hover
icon: icon.png

parameters:
    input_ref:
        ui-name: Genome DataLake Tables
        short-hint: Select a GenomeDataLakeTables object
        long-hint: |
            Select a GenomeDataLakeTables object from your workspace.
            This object contains genome data for visualization.

description: |
    <p>This app does something useful.</p>

    <p><strong>Input:</strong></p>
    <ul>
        <li><b>Genome DataLake Tables</b> - Description</li>
    </ul>

    <p><strong>Output:</strong></p>
    <ul>
        <li>An interactive HTML report</li>
    </ul>

publications:
    - pmid: 12345678
      display-text: "Author et al. 2020"
      link: https://doi.org/10.1234/example
```

### Widget Types

**Output Widgets:**
- `"no-display"` - Report-based apps (most common)
- `"kbaseReportView"` - Display KBase reports
- `null` - Default input widget

**Parameter Field Types:**
- `"text"` - Text input with optional workspace object validation
- `"int"` - Integer with min/max
- `"float"` - Float with min/max
- `"dropdown"` - Enumerated options
- `"checkbox"` - Boolean
- `"textarea"` - Multi-line text

---

## 6. Development Workflow

### Step 1: Initialize Module

```bash
kb-sdk init --language python --user jplfaria jplfariaDashboard
cd jplfariaDashboard
```

### Step 2: Define Interface (KIDL)

Edit `jplfariaDashboard.spec`:

```kidl
module jplfariaDashboard {
    typedef structure {
        string workspace_name;
        string input_ref;
    } DashboardParams;

    typedef structure {
        string report_name;
        string report_ref;
    } ReportResults;

    funcdef run_dashboard(DashboardParams params)
        returns (ReportResults output)
        authentication required;
};
```

### Step 3: Compile Specification

```bash
make
```

This generates:
- `lib/jplfariaDashboard/jplfariaDashboardServer.py`
- `lib/jplfariaDashboard/jplfariaDashboardImpl.py` (skeleton)

### Step 4: Implement Method

Edit `lib/jplfariaDashboard/jplfariaDashboardImpl.py`:

```python
def run_dashboard(self, ctx, params):
    # 1. Validate
    if 'workspace_name' not in params:
        raise ValueError('workspace_name is required')

    # 2. Do work
    html_dir = os.path.join(self.scratch, str(uuid.uuid4()))
    shutil.copytree('/kb/module/data/html', html_dir)

    # 3. Upload to Shock
    shock_id = self.dfu.file_to_shock({
        'file_path': html_dir,
        'pack': 'zip'
    })['shock_id']

    # 4. Create report
    report = self.kr.create_extended_report({
        'direct_html_link_index': 0,
        'html_links': [{'shock_id': shock_id, 'name': 'index.html'}],
        'workspace_name': params['workspace_name']
    })

    return {'report_name': report['name'], 'report_ref': report['ref']}
```

### Step 5: Configure UI

Edit `ui/narrative/methods/run_dashboard/spec.json` and `display.yaml`

### Step 6: Test Locally

```bash
kb-sdk test
```

This:
- Builds Docker image
- Runs tests in `test/jplfariaDashboard_server_test.py`
- Validates against KBase services

### Step 7: Version Control

```bash
git init
git add .
git commit -m "Initial implementation"
git remote add origin git@github.com:jplfaria/jplfariaDashboard.git
git push -u origin master
```

### Step 8: Register Module

```bash
kb-sdk register
```

Prompts for GitHub repo URL, validates, registers with KBase.

### Step 9: Deploy to Environments

- **Appdev** (development): Auto-deploys on push to master
- **Next** (staging): Manual promotion from appdev
- **Prod** (production): Manual promotion from next

---

## 7. Dependencies and Integration

### Python Dependencies

Add to `requirements.txt`:
```
pandas
numpy
matplotlib
```

### System Dependencies

Add to `Dockerfile`:
```dockerfile
RUN apt-get install -y blast+ hmmer
```

### Other KB SDK Modules

Add to `dependencies.json`:
```json
{
    "DataFileUtil": {
        "module_name": "DataFileUtil",
        "version": "release"
    },
    "KBaseReport": {
        "module_name": "KBaseReport",
        "version": "release"
    }
}
```

### KBUtilLib Integration

**What is KBUtilLib?**
A modular utility framework providing reusable code for common KB operations.

**Installation:**
```dockerfile
RUN pip install git+https://github.com/kbase/KBUtilLib.git
```

**Usage via Multiple Inheritance:**
```python
from KBUtilLib.KBWSUtils import KBWSUtils
from KBUtilLib.KBGenomeUtils import KBGenomeUtils

class MyModule(KBWSUtils, KBGenomeUtils):
    def __init__(self, config):
        super().__init__(config)

    def my_method(self, ctx, params):
        # Use KBWSUtils methods
        genome_obj = self.get_object(params['workspace_name'], params['genome_ref'])

        # Use KBGenomeUtils methods
        features = self.get_features_by_type(genome_obj, 'CDS')
```

**Available Utility Classes:**
- `KBWSUtils` - Workspace operations
- `KBGenomeUtils` - Genome data extraction
- `KBModelUtils` - Metabolic model operations
- `MSBiochemUtils` - Biochemistry database queries
- `KBAnnotationUtils` - Annotation processing

---

## 8. Reports and HTML Output

### Simple Text Report

```python
report = self.kr.create({
    'report': {
        'text_message': 'Analysis complete! Found 42 genes.',
        'warnings': ['Low coverage in contig 3']
    },
    'workspace_name': workspace_name
})
```

### HTML Report

```python
html = '<h1>Results</h1><p>Analysis found 42 genes.</p>'

report = self.kr.create_extended_report({
    'direct_html': html,
    'report_object_name': 'my_report_' + str(uuid.uuid4()),
    'workspace_name': workspace_name
})
```

### HTML Report with Files

```python
# Prepare HTML directory
html_dir = os.path.join(self.scratch, 'html')
shutil.copytree('/kb/module/data/html', html_dir)

# Write configuration
with open(os.path.join(html_dir, 'config.json'), 'w') as f:
    json.dump({'upa': params['input_ref']}, f)

# Upload to Shock
shock_id = self.dfu.file_to_shock({
    'file_path': html_dir,
    'make_handle': 0,
    'pack': 'zip'
})['shock_id']

# Create report
report = self.kr.create_extended_report({
    'direct_html_link_index': 0,
    'html_links': [{
        'shock_id': shock_id,
        'name': 'index.html',
        'label': 'Dashboard'
    }],
    'html_window_height': 800,
    'report_object_name': 'dashboard_' + str(uuid.uuid4()),
    'workspace_name': workspace_name
})
```

### Downloadable Files

```python
report = self.kr.create_extended_report({
    'file_links': [{
        'path': '/path/to/results.csv',
        'name': 'results.csv',
        'label': 'Analysis Results',
        'description': 'CSV file with gene annotations'
    }],
    'workspace_name': workspace_name
})
```

---

## 9. Reference Data

### Including Reference Data

Put files in `data/` directory:
```
MyModule/
└── data/
    ├── reference_genomes.fasta
    ├── hmm_profiles/
    └── html/
        ├── index.html
        ├── assets/
        └── config/
```

### Accessing Reference Data

In Docker, module is at `/kb/module`:

```python
ref_file = '/kb/module/data/reference_genomes.fasta'
html_dir = '/kb/module/data/html'
```

### Size Limits

- **Docker image**: Keep under 10 GB
- **Reference data**: Keep under 5 GB
- **For larger datasets**: Use workspace objects or external URLs

---

## 10. Testing

### Unit Test Structure

`test/MyModule_server_test.py`:

```python
import unittest
import os
from MyModule.MyModuleImpl import MyModule
from MyModule.MyModuleServer import MethodContext

class MyModuleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = os.environ.get('KB_AUTH_TOKEN', None)
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('MyModule'):
            cls.cfg[nameval[0]] = nameval[1]
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = Workspace(cls.wsURL, token=token)
        cls.serviceImpl = MyModule(cls.cfg)
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token, 'provenance': [{}], 'authenticated': 1})

    def test_my_method(self):
        # Setup test data
        params = {
            'workspace_name': 'MyWorkspace',
            'input_ref': '12345/67/1'
        }

        # Call method
        result = self.serviceImpl.my_method(self.ctx, params)[0]

        # Verify
        self.assertIn('report_name', result)
        self.assertIn('report_ref', result)
```

### Running Tests

```bash
# Local (requires Docker)
kb-sdk test

# In container
make test
```

---

## 11. Deployment and Versioning

### Version Management

Edit `kbase.yml`:
```yaml
module-version: 0.1.0
```

Semantic versioning: `MAJOR.MINOR.PATCH`
- MAJOR: Breaking changes
- MINOR: New features
- PATCH: Bug fixes

### Git Tag for Release

```bash
git tag -a v0.1.0 -m "First release"
git push origin v0.1.0
```

### Deployment Environments

1. **AppDev** (CI.kbase.us)
   - Auto-deploys from master branch
   - For testing and development
   - No user data

2. **Next** (next.kbase.us)
   - Staging environment
   - Pre-production testing
   - Manual promotion

3. **Production** (narrative.kbase.us)
   - Live environment
   - Manual promotion only
   - Full user data

### Promotion Process

```bash
kb-sdk release --dev  # Deploy to appdev
kb-sdk release --beta # Promote to next
kb-sdk release        # Promote to production
```

---

## 12. KB SDK Plus (Modernization)

### What is KB SDK Plus?

A modernized version of KB SDK with:
- **Better dependency management** - Uses `uv` instead of pip
- **Modern Java** - Requires Java 17 (current LTS)
- **Gradle build system** - Instead of Make
- **Updated tooling** - More automated code generation

### Status

- **Version:** 0.1.0-alpha6 (pre-release)
- **Stability:** Alpha - experimental, not production-ready
- **Recommendation:** Stick with standard KB SDK for now

---

## 13. Chris Henry's ClaudeCommands Integration

### What is ClaudeCommands?

A framework for running Claude Code in headless mode with standardized command patterns for:
- Creating PRDs (Product Requirements Documents)
- Generating implementation tasks
- Documenting code architecture
- Documenting public APIs

### KB SDK Development Commands

Located in `commands/kb-sdk-dev/`:

**Context files:**
- `kidl-reference.md` - KIDL syntax guide
- `ui-spec-reference.md` - UI configuration patterns
- `kbutillib-integration.md` - KBUtilLib usage
- `workspace-datatypes.md` - KBase type system

**Expert commands:**
- `kbutillib-expert.md` - KBUtilLib specialist
- `fbapkg-expert.md` - FBA modeling specialist
- `modelseeddb-expert.md` - ModelSEED database specialist

### Integration with Our Workflow

1. Use context files as reference for KB SDK patterns
2. ClaudeCommands can generate KB SDK modules
3. Standardized workflow for KB SDK app development

---

## 14. Best Practices Summary

### DO:
✅ Use KBUtilLib for common operations (avoid reinventing wheel)
✅ Write comprehensive KIDL documentation (becomes API docs)
✅ Include meaningful error messages
✅ Test thoroughly in appdev before promoting
✅ Version semantic properly
✅ Document UI parameters with helpful hints
✅ Keep Docker images lean
✅ Use workspace objects for large datasets
✅ Create reports with HTML for rich visualization
✅ Follow KBase naming conventions

### DON'T:
❌ Edit auto-generated server files
❌ Skip authentication when required
❌ Hardcode file paths (use scratch directory)
❌ Bundle large reference data in Docker
❌ Skip parameter validation
❌ Use non-standard Python packages without testing
❌ Deploy directly to production
❌ Forget to update version numbers
❌ Skip UI documentation
❌ Ignore test failures

---

## 15. Integration Strategy for Genome Heatmap Viewer

### Approach: Extend KBDatalakeDashboard

**Why?**
- Already has GenomeDataLakeTables input type
- Dashboard HTML infrastructure in place
- Authentication and Shock upload working
- Just need to add heatmap HTML

**Steps:**

1. **Add Heatmap HTML to data/ directory:**
   ```
   KBDatalakeDashboard/
   └── data/
       ├── html/          # Existing dashboard
       └── heatmap/       # NEW - Genome heatmap viewer
           ├── index.html
           ├── genes_data.json (template)
           └── config/
   ```

2. **Modify KBDatalakeDashboardImpl.py:**
   ```python
   # Copy heatmap HTML too
   shutil.copytree('/kb/module/data/heatmap', f'{html_dir}/heatmap')

   # Add second HTML link
   html_links = [
       {'shock_id': shock_id, 'name': 'index.html', 'label': 'Data Tables'},
       {'shock_id': shock_id, 'name': 'heatmap/index.html', 'label': 'Gene Heatmap'}
   ]
   ```

3. **Update heatmap HTML to fetch data:**
   ```javascript
   // Read ../app-config.json for UPA
   const config = await fetch('../app-config.json').then(r => r.json());

   // Fetch genes from TableScanner API
   const genes = await fetchGenesData(config.upa);

   // Render heatmap
   renderHeatmap(genes);
   ```

4. **Test in appdev:**
   ```bash
   make
   kb-sdk test
   git commit -am "Add genome heatmap viewer"
   git push
   # Wait for appdev deployment
   # Test in CI narrative
   ```

5. **Deploy:**
   ```bash
   kb-sdk release --dev   # Confirm appdev
   kb-sdk release --beta  # Promote to next
   kb-sdk release         # Promote to production
   ```

---

## Summary

KB SDK development is **specification-driven, Docker-based, and highly automated**. You define interfaces in KIDL, implement methods in Python, configure UIs in JSON/YAML, and the SDK handles server generation, deployment, testing, and versioning. The key to success is understanding the auto-generated vs manually-edited file distinction and following KBase conventions for workspace operations, reports, and data types.

**For our genome heatmap integration:** We'll extend KBDatalakeDashboard by adding heatmap HTML to the data directory and modifying the implementation to include it in the report. This leverages existing infrastructure while adding our visualization as a separate tab.

**Ready to start development!** 🚀

