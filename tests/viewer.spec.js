// @ts-check
const { test, expect } = require('@playwright/test');

// =============================================================================
// KNOWN DATA CONSTANTS (verified from genes_data.json and DB)
// These are the ground-truth values our viewer should match.
// =============================================================================
const EXPECTED = {
  totalGenes: 4617,
  coreGenes: 3626,
  accessoryGenes: 587,
  unknownGenes: 404,
  // 3626 + 587 + 404 = 4617
  nRefGenomes: 35,
  nTotalGenomes: 36, // 35 ref + 1 user
  userGenomeId: '562.61143',
};

// =============================================================================
// TRACKS TAB - FUNCTIONALITY
// =============================================================================
test.describe('Tracks Tab - Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#kpi-bar .kpi-stat');
  });

  test('page loads with correct title', async ({ page }) => {
    await expect(page).toHaveTitle('Datalake Dashboard');
  });

  test('Tracks tab is active by default', async ({ page }) => {
    const tracksBtn = page.locator('.tab-btn[data-tab="tracks"]');
    await expect(tracksBtn).toHaveClass(/active/);
  });

  test('5 default tracks are enabled', async ({ page }) => {
    const checked = page.locator('#track-list input[type="checkbox"]:checked');
    await expect(checked).toHaveCount(5);
  });

  test('gene search works and returns results', async ({ page }) => {
    await page.fill('#gene-search', 'kinase');
    await page.waitForTimeout(300);
    const info = page.locator('#search-info');
    await expect(info).toBeVisible();
    const text = await info.textContent();
    const matchCount = parseInt(text);
    expect(matchCount).toBeGreaterThan(50);
    expect(matchCount).toBeLessThan(300);
  });

  test('search for known gene by FID', async ({ page }) => {
    await page.fill('#gene-search', 'dnaA');
    await page.waitForTimeout(300);
    const info = page.locator('#search-info');
    await expect(info).toBeVisible();
    const text = await info.textContent();
    const matchCount = parseInt(text);
    expect(matchCount).toBeGreaterThanOrEqual(1);
  });

  test('sort by Conservation works', async ({ page }) => {
    await page.click('button:has-text("Conservation"):not(.tab-btn)');
    const info = page.locator('#info');
    await expect(info).toHaveText('Sorted by: Conservation');
  });

  test('zoom slider changes visible gene range', async ({ page }) => {
    const info = page.locator('#position-info');
    const beforeText = await info.textContent();
    // Default zoom shows all genes
    expect(beforeText).toContain('0 - 4617 of 4617');

    // Zoom in
    await page.fill('#zoom-slider', '10');
    await page.dispatchEvent('#zoom-slider', 'input');
    await page.waitForTimeout(100);
    const afterText = await info.textContent();
    // Should show a subset
    expect(afterText).not.toContain('0 - 4617 of 4617');
    expect(afterText).toContain('of 4617');
  });

  test('minimap is visible and shows overview', async ({ page }) => {
    const minimap = page.locator('#genome-minimap');
    await expect(minimap).toBeVisible();
    const label = page.locator('#minimap-label');
    await expect(label).toContainText('Overview:');
  });

  test('minimap click-to-jump updates position', async ({ page }) => {
    // Zoom in first so there's a scroll range
    await page.fill('#zoom-slider', '10');
    await page.dispatchEvent('#zoom-slider', 'input');
    await page.waitForTimeout(100);

    const canvas = page.locator('#minimap-canvas');
    const box = await canvas.boundingBox();
    // Click in the middle
    await canvas.click({ position: { x: box.width / 2, y: box.height / 2 } });
    await page.waitForTimeout(100);

    const info = await page.locator('#position-info').textContent();
    // Should be around the middle of the genome
    const match = info.match(/(\d+) - (\d+)/);
    expect(match).not.toBeNull();
    const start = parseInt(match[1]);
    expect(start).toBeGreaterThan(1000);
    expect(start).toBeLessThan(3500);
  });

  test('analysis view activates correct tracks', async ({ page }) => {
    // Click "Characterization Targets"
    await page.click('button.analysis-view-btn:has-text("Characterization Targets")');
    await page.waitForTimeout(100);

    // Should enable: is_hypo, pan_category, conservation, avg_cons
    const checkedLabels = await page.locator('#track-list .track-item.active label').allTextContents();
    expect(checkedLabels).toContain('Hypothetical Protein');
    expect(checkedLabels).toContain('Core/Accessory');
    expect(checkedLabels).toContain('Pangenome Conservation');
    expect(checkedLabels).toContain('Function Consensus (avg)');
  });

  test('gene detail panel opens on heatmap click', async ({ page }) => {
    // Click somewhere on the heatmap canvas
    const canvas = page.locator('#heatmap');
    const box = await canvas.boundingBox();
    await canvas.click({ position: { x: 300, y: 20 } });
    await page.waitForTimeout(100);

    const panel = page.locator('#gene-detail-panel');
    await expect(panel).toHaveClass(/open/);
    const title = page.locator('#detail-title');
    const text = await title.textContent();
    expect(text).toMatch(/Gene .+/);
  });

  test('reset zoom returns to full view', async ({ page }) => {
    await page.fill('#zoom-slider', '10');
    await page.dispatchEvent('#zoom-slider', 'input');
    await page.waitForTimeout(100);
    await page.click('button:has-text("Reset")');
    await page.waitForTimeout(100);
    const info = await page.locator('#position-info').textContent();
    expect(info).toContain('0 - 4617 of 4617');
  });
});

// =============================================================================
// TRACKS TAB - DATA CORRECTNESS
// =============================================================================
test.describe('Tracks Tab - Data Correctness', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#kpi-bar .kpi-stat');
  });

  test('KPI total genes is correct', async ({ page }) => {
    const kpiValues = await page.locator('#kpi-bar .kpi-value').allTextContents();
    expect(kpiValues[0]).toBe(String(EXPECTED.totalGenes));
  });

  test('KPI core/accessory/unknown sum equals total', async ({ page }) => {
    const kpiValues = await page.locator('#kpi-bar .kpi-value').allTextContents();
    const total = parseInt(kpiValues[0]);
    const core = parseInt(kpiValues[1]);
    const accessory = parseInt(kpiValues[2]);
    const unknown = parseInt(kpiValues[3]);

    expect(core).toBe(EXPECTED.coreGenes);
    expect(accessory).toBe(EXPECTED.accessoryGenes);
    expect(unknown).toBe(EXPECTED.unknownGenes);
    expect(core + accessory + unknown).toBe(total);
  });

  test('KPI avg consistency is between 0 and 1', async ({ page }) => {
    const kpiValues = await page.locator('#kpi-bar .kpi-value').allTextContents();
    const avgCons = parseFloat(kpiValues[4]);
    expect(avgCons).toBeGreaterThan(0);
    expect(avgCons).toBeLessThanOrEqual(1.0);
  });

  test('KPI low consistency count is reasonable', async ({ page }) => {
    const kpiValues = await page.locator('#kpi-bar .kpi-value').allTextContents();
    const lowCons = parseInt(kpiValues[5]);
    // Low consistency should be a subset of genes with clusters
    expect(lowCons).toBeGreaterThan(0);
    expect(lowCons).toBeLessThan(EXPECTED.totalGenes);
  });

  test('KPI no-cluster count equals unknown genes (pangenome-unclustered)', async ({ page }) => {
    const kpiValues = await page.locator('#kpi-bar .kpi-value').allTextContents();
    const noCluster = parseInt(kpiValues[6]);
    // No-cluster should match unknown count (genes with avg_cons < 0)
    expect(noCluster).toBe(EXPECTED.unknownGenes);
  });

  test('default 5 tracks have correct names', async ({ page }) => {
    const activeLabels = await page.locator('#track-list .track-item.active label').allTextContents();
    expect(activeLabels).toEqual([
      'Gene Order',
      'Gene Direction',
      'Pangenome Conservation',
      'Core/Accessory',
      'Function Consensus (avg)',
    ]);
  });

  test('all 30 tracks are listed (24 data + 6 placeholder)', async ({ page }) => {
    const allLabels = await page.locator('#track-list .track-item label').allTextContents();
    expect(allLabels.length).toBe(30);
    // Check for key tracks
    expect(allLabels).toContain('Pangenome Conservation');
    expect(allLabels).toContain('RAST Consistency');
    expect(allLabels).toContain('KO Consistency');
    expect(allLabels).toContain('EC Consistency');
    expect(allLabels).toContain('Bakta Consistency');
    expect(allLabels).toContain('Protein Length');
  });

  test('sort presets have correct names', async ({ page }) => {
    const presetNames = await page.locator('.sort-preset-btn').allTextContents();
    expect(presetNames).toEqual([
      'Genome Order',
      'Conservation',
      'Consistency',
      'Annotation Depth',
      'Pangenome Status',
      'Lowest Consistency',
      'Strand Blocks',
    ]);
  });

  test('gene detail shows valid data for a clicked gene', async ({ page }) => {
    // Click on the heatmap to get a gene
    const canvas = page.locator('#heatmap');
    await canvas.click({ position: { x: 300, y: 20 } });
    await page.waitForTimeout(200);

    const panel = page.locator('#gene-detail-panel');
    await expect(panel).toHaveClass(/open/);

    // Check that pangenome category is one of the valid values
    const bodyHtml = await page.locator('#detail-body').innerHTML();
    expect(bodyHtml).toMatch(/Core|Accessory|Unknown/);

    // Check conservation is a percentage
    expect(bodyHtml).toMatch(/\d+\.\d+%/);

    // Check consistency scores exist
    expect(bodyHtml).toMatch(/Average/);
    expect(bodyHtml).toMatch(/RAST/);
    expect(bodyHtml).toMatch(/Bakta/);

    // Check protein length is positive
    const protLenMatch = bodyHtml.match(/(\d+) aa/);
    expect(protLenMatch).not.toBeNull();
    const protLen = parseInt(protLenMatch[1]);
    expect(protLen).toBeGreaterThan(0);
    expect(protLen).toBeLessThan(5000);
  });

  test('legend shows correct color scheme labels', async ({ page }) => {
    const legendText = await page.locator('#legend').textContent();
    // Default tracks include sequential, consistency, binary (strand), categorical (pangenome)
    expect(legendText).toContain('Gradient:');
    expect(legendText).toContain('Low');
    expect(legendText).toContain('High');
    expect(legendText).toContain('Consistency:');
    expect(legendText).toContain('N/A');
    expect(legendText).toContain('Strand:');
    expect(legendText).toContain('Forward (+)');
    expect(legendText).toContain('Reverse (-)');
    expect(legendText).toContain('Pangenome:');
    expect(legendText).toContain('Unknown');
    expect(legendText).toContain('Accessory');
    expect(legendText).toContain('Core');
  });

  test('6 analysis views are listed with correct names', async ({ page }) => {
    const viewNames = await page.locator('.analysis-view-btn .av-name').allTextContents();
    expect(viewNames).toEqual([
      'Characterization Targets',
      'Annotation Quality',
      'Metabolic Landscape',
      'Pangenome Structure',
      'Knowledge Coverage',
      'Consistency Comparison',
    ]);
  });

  test('genes data integrity - verify against loaded JSON', async ({ page }) => {
    // Directly verify genes_data.json was loaded correctly
    const geneCount = await page.evaluate(() => genes.length);
    expect(geneCount).toBe(EXPECTED.totalGenes);

    // Check first gene has expected fields
    const firstGene = await page.evaluate(() => genes[0]);
    expect(firstGene.length).toBe(29); // 29 fields per gene

    // Verify field indices are correct
    const fieldCheck = await page.evaluate(() => {
      const g = genes[0];
      return {
        hasId: typeof g[F.ID] === 'number',
        hasFid: typeof g[F.FID] === 'string' || typeof g[F.FID] === 'number',
        hasLength: typeof g[F.LENGTH] === 'number' && g[F.LENGTH] > 0,
        hasStart: typeof g[F.START] === 'number',
        strandValid: g[F.STRAND] === 0 || g[F.STRAND] === 1,
        consFracRange: g[F.CONS_FRAC] >= 0 && g[F.CONS_FRAC] <= 1,
        panCatValid: [0, 1, 2].includes(g[F.PAN_CAT]),
      };
    });
    expect(fieldCheck.hasId).toBe(true);
    expect(fieldCheck.hasFid).toBe(true);
    expect(fieldCheck.hasLength).toBe(true);
    expect(fieldCheck.hasStart).toBe(true);
    expect(fieldCheck.strandValid).toBe(true);
    expect(fieldCheck.consFracRange).toBe(true);
    expect(fieldCheck.panCatValid).toBe(true);
  });

  test('conservation sort orders genes from high to low', async ({ page }) => {
    await page.click('button:has-text("Conservation"):not(.tab-btn)');
    await page.waitForTimeout(100);

    const consValues = await page.evaluate(() => {
      // Get first 20 and last 20 sorted genes' conservation values
      const first = sortedIndices.slice(0, 20).map(i => genes[i][F.CONS_FRAC]);
      const last = sortedIndices.slice(-20).map(i => genes[i][F.CONS_FRAC]);
      return { first, last };
    });

    // First genes should have high conservation
    const avgFirst = consValues.first.reduce((a, b) => a + b) / consValues.first.length;
    const avgLast = consValues.last.reduce((a, b) => a + b) / consValues.last.length;
    expect(avgFirst).toBeGreaterThan(avgLast);
    expect(avgFirst).toBeGreaterThan(0.8); // Top genes should be >80% conserved
  });
});

// =============================================================================
// TREE TAB - FUNCTIONALITY
// =============================================================================
test.describe('Tree Tab - Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#kpi-bar .kpi-stat');
    await page.click('.tab-btn[data-tab="tree"]');
    await page.waitForSelector('.tree-leaf', { timeout: 10000 });
  });

  test('Tree tab loads and shows SVG dendrogram', async ({ page }) => {
    const svg = page.locator('#tree-container svg');
    await expect(svg).toBeVisible();
  });

  test('all 36 genome leaves are rendered', async ({ page }) => {
    const leaves = page.locator('.tree-leaf');
    await expect(leaves).toHaveCount(EXPECTED.nTotalGenomes);
  });

  test('user genome leaf is highlighted', async ({ page }) => {
    const userLeaf = page.locator('.tree-leaf.user-genome');
    await expect(userLeaf).toHaveCount(1);
    const text = await userLeaf.textContent();
    expect(text).toContain(EXPECTED.userGenomeId);
    expect(text).toContain('YOUR GENOME');
  });

  test('stat bar checkboxes toggle bars', async ({ page }) => {
    // Initially 3 stat bars enabled
    const checkedBoxes = page.locator('#tree-stat-toggles input[type="checkbox"]:checked');
    await expect(checkedBoxes).toHaveCount(3);
  });

  test('leaf hover shows tooltip with genome metadata', async ({ page }) => {
    const firstLeaf = page.locator('.tree-leaf').first();
    await firstLeaf.hover();
    await page.waitForTimeout(200);
    const tooltip = page.locator('#tree-tooltip');
    await expect(tooltip).toBeVisible();
    const text = await tooltip.textContent();
    // Should contain genome metadata
    expect(text).toMatch(/Features:|Contigs:|Genes:|Clusters:/);
  });
});

// =============================================================================
// TREE TAB - DATA CORRECTNESS
// =============================================================================
test.describe('Tree Tab - Data Correctness', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#kpi-bar .kpi-stat');
    await page.click('.tab-btn[data-tab="tree"]');
    await page.waitForSelector('.tree-leaf', { timeout: 10000 });
  });

  test('tree info shows correct genome count', async ({ page }) => {
    const infoText = await page.locator('#tree-info').textContent();
    expect(infoText).toContain('36');
    expect(infoText).toContain('35 reference + user');
  });

  test('tree info shows reasonable Jaccard distance range', async ({ page }) => {
    const infoText = await page.locator('#tree-info').textContent();
    // Jaccard distances should be between 0 and 1
    const distMatch = infoText.match(/(\d+\.\d+)\s*-\s*(\d+\.\d+)/);
    expect(distMatch).not.toBeNull();
    const minDist = parseFloat(distMatch[1]);
    const maxDist = parseFloat(distMatch[2]);
    expect(minDist).toBeGreaterThan(0);
    expect(minDist).toBeLessThan(0.1); // Closest genomes should be very similar
    expect(maxDist).toBeGreaterThan(0.3); // Most distant should be meaningfully different
    expect(maxDist).toBeLessThan(1.0); // All E. coli, so shouldn't be fully different
  });

  test('user genome info shows correct gene count and core percentage', async ({ page }) => {
    const infoText = await page.locator('#tree-info').textContent();
    expect(infoText).toContain(EXPECTED.userGenomeId);
    expect(infoText).toContain('4617 genes');
    // Core percentage should be reasonable for E. coli (>60%)
    const corePctMatch = infoText.match(/(\d+\.\d+)% core/);
    expect(corePctMatch).not.toBeNull();
    const corePct = parseFloat(corePctMatch[1]);
    expect(corePct).toBeGreaterThan(60);
    expect(corePct).toBeLessThan(100);
  });

  test('dendrogram has scale axis label', async ({ page }) => {
    const svgText = await page.locator('#tree-container svg').textContent();
    expect(svgText).toContain('Jaccard distance');
  });

  test('stat bar headers are correct', async ({ page }) => {
    const svgText = await page.locator('#tree-container svg').textContent();
    expect(svgText).toContain('Genes');
    expect(svgText).toContain('Clusters');
    expect(svgText).toContain('Core %');
  });

  test('all genome IDs in tree are valid accessions or user genome', async ({ page }) => {
    const gids = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('.tree-leaf')).map(el => el.getAttribute('data-gid'));
    });
    expect(gids.length).toBe(EXPECTED.nTotalGenomes);

    const userCount = gids.filter(g => g === EXPECTED.userGenomeId).length;
    expect(userCount).toBe(1);

    // Reference genomes have GCF_ in the ID (may have RS_ prefix and .1 suffix)
    const gcfCount = gids.filter(g => g.includes('GCF_')).length;
    expect(gcfCount).toBe(EXPECTED.nRefGenomes);
  });

  test('tree toolbar shows correct description', async ({ page }) => {
    const toolbar = page.locator('#tree-toolbar');
    const text = await toolbar.textContent();
    expect(text).toContain('UPGMA');
    expect(text).toContain('Jaccard');
    expect(text).toContain('pangenome cluster');
  });
});

// =============================================================================
// CLUSTER TAB - FUNCTIONALITY
// =============================================================================
test.describe('Cluster Tab - Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#kpi-bar .kpi-stat');
    await page.click('.tab-btn[data-tab="cluster"]');
    await page.waitForSelector('#cluster-canvas', { timeout: 10000 });
    await page.waitForTimeout(500); // wait for render
  });

  test('Cluster tab loads and shows canvas', async ({ page }) => {
    const canvas = page.locator('#cluster-canvas');
    await expect(canvas).toBeVisible();
  });

  test('embedding dropdown has correct options', async ({ page }) => {
    const options = await page.locator('#cluster-embedding option').allTextContents();
    expect(options).toEqual(['Gene Features', 'Presence/Absence']);
  });

  test('color-by dropdown has correct options', async ({ page }) => {
    const options = await page.locator('#cluster-color-by option').allTextContents();
    expect(options).toEqual([
      'Core/Accessory', 'Conservation', 'Avg Consistency', 'Hypothetical',
      'Localization', '# KEGG Terms', 'Module Hits', 'Cluster Size',
      'Specificity', 'RAST/Bakta Agreement',
    ]);
  });

  test('switching embedding to Presence/Absence works', async ({ page }) => {
    await page.selectOption('#cluster-embedding', 'presence');
    await page.waitForTimeout(200);
    const desc = await page.locator('#cluster-embed-desc').textContent();
    expect(desc).toContain('presence/absence');
    expect(desc).toContain('35 reference genomes');
  });

  test('cluster search finds genes', async ({ page }) => {
    await page.fill('#cluster-search', 'kinase');
    await page.waitForTimeout(300);
    const info = page.locator('#cluster-search-info');
    await expect(info).toBeVisible();
    const text = await info.textContent();
    const count = parseInt(text);
    expect(count).toBeGreaterThan(50);
  });

  test('changing color-by updates legend', async ({ page }) => {
    // Default is Core/Accessory
    let legend = await page.locator('#cluster-legend').textContent();
    expect(legend).toContain('Core');
    expect(legend).toContain('Accessory');

    // Switch to Hypothetical
    await page.selectOption('#cluster-color-by', 'is_hypo');
    await page.waitForTimeout(200);
    legend = await page.locator('#cluster-legend').textContent();
    expect(legend).toContain('Has function');
    expect(legend).toContain('Hypothetical');
  });
});

// =============================================================================
// CLUSTER TAB - DATA CORRECTNESS
// =============================================================================
test.describe('Cluster Tab - Data Correctness', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#kpi-bar .kpi-stat');
    await page.click('.tab-btn[data-tab="cluster"]');
    await page.waitForSelector('#cluster-canvas', { timeout: 10000 });
    await page.waitForTimeout(500);
  });

  test('cluster info shows correct gene count', async ({ page }) => {
    const infoText = await page.locator('#cluster-info').textContent();
    expect(infoText).toContain('4,617');
    expect(infoText).toContain('genes plotted');
  });

  test('cluster info shows correct pangenome breakdown', async ({ page }) => {
    const infoText = await page.locator('#cluster-info').textContent();
    expect(infoText).toContain(`${EXPECTED.coreGenes} core`);
    expect(infoText).toContain(`${EXPECTED.accessoryGenes} accessory`);
    expect(infoText).toContain(`${EXPECTED.unknownGenes} unknown`);
  });

  test('cluster toolbar shows gene count', async ({ page }) => {
    const toolbar = await page.locator('#cluster-toolbar-info').textContent();
    expect(toolbar).toContain('4,617 genes');
  });

  test('cluster data has correct number of points', async ({ page }) => {
    const nPoints = await page.evaluate(() => {
      return clusterData && clusterData.features ? clusterData.features.x.length : 0;
    });
    expect(nPoints).toBe(EXPECTED.totalGenes);
  });

  test('Gene Features embedding description is accurate', async ({ page }) => {
    const desc = await page.locator('#cluster-embed-desc').textContent();
    expect(desc).toContain('conservation');
    expect(desc).toContain('consistency');
    expect(desc).toContain('annotation');
  });

  test('Presence/Absence embedding mentions reference genomes', async ({ page }) => {
    await page.selectOption('#cluster-embedding', 'presence');
    await page.waitForTimeout(100);
    const desc = await page.locator('#cluster-embed-desc').textContent();
    expect(desc).toContain('35 reference genomes');
  });
});

// =============================================================================
// SCIENTIFIC CORRECTNESS - Cross-tab data consistency
// =============================================================================
test.describe('Scientific Correctness', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#kpi-bar .kpi-stat');
  });

  test('pangenome categories are biologically reasonable for E. coli', async ({ page }) => {
    // E. coli should have majority core genome
    const kpiValues = await page.locator('#kpi-bar .kpi-value').allTextContents();
    const core = parseInt(kpiValues[1]);
    const total = parseInt(kpiValues[0]);
    const coreFraction = core / total;

    // Core genome should be 60-90% of total for E. coli
    expect(coreFraction).toBeGreaterThan(0.6);
    expect(coreFraction).toBeLessThan(0.9);
  });

  test('average consistency is in expected range for pangenome analysis', async ({ page }) => {
    const kpiValues = await page.locator('#kpi-bar .kpi-value').allTextContents();
    const avgCons = parseFloat(kpiValues[4]);
    // Average consistency should be moderate-to-high (0.5-0.95)
    // If it were near 0, annotations would be garbage; near 1.0 would mean no variation
    expect(avgCons).toBeGreaterThan(0.5);
    expect(avgCons).toBeLessThan(0.95);
  });

  test('conservation sort: core genes at top, unknown at bottom', async ({ page }) => {
    await page.click('button:has-text("Conservation"):not(.tab-btn)');
    await page.waitForTimeout(100);

    const result = await page.evaluate(() => {
      // Check top genes are core and bottom genes are unknown/accessory
      const topCats = sortedIndices.slice(0, 100).map(i => genes[i][F.PAN_CAT]);
      const bottomCats = sortedIndices.slice(-100).map(i => genes[i][F.PAN_CAT]);
      const topCoreCount = topCats.filter(c => c === 2).length;
      const bottomUnknownCount = bottomCats.filter(c => c === 0).length;
      return { topCoreCount, bottomUnknownCount };
    });

    // Top 100 by conservation should be overwhelmingly core
    expect(result.topCoreCount).toBeGreaterThan(90);
    // Bottom 100 should have many unknown genes
    expect(result.bottomUnknownCount).toBeGreaterThan(50);
  });

  test('consistency scores correctly flag N/A for unclustered genes', async ({ page }) => {
    const result = await page.evaluate(() => {
      // Genes with pangenome category 0 (unknown) should have consistency = -1 (N/A)
      const unknownGenes = genes.filter(g => g[F.PAN_CAT] === 0);
      const naCount = unknownGenes.filter(g => g[F.AVG_CONS] === -1).length;
      return { unknownCount: unknownGenes.length, naCount };
    });

    // All or nearly all unknown genes should have N/A consistency
    expect(result.naCount).toBe(result.unknownCount);
  });

  test('strand distribution is biologically reasonable', async ({ page }) => {
    const result = await page.evaluate(() => {
      const forward = genes.filter(g => g[F.STRAND] === 1).length;
      return { forward, total: genes.length };
    });

    // E. coli has roughly 50-55% forward strand genes
    const fwdFrac = result.forward / result.total;
    expect(fwdFrac).toBeGreaterThan(0.4);
    expect(fwdFrac).toBeLessThan(0.65);
  });

  test('protein lengths are in realistic range', async ({ page }) => {
    const result = await page.evaluate(() => {
      const lens = genes.map(g => g[F.PROT_LEN]);
      const min = Math.min(...lens);
      const max = Math.max(...lens);
      const avg = lens.reduce((a, b) => a + b) / lens.length;
      return { min, max, avg };
    });

    // Protein lengths: min should be >20 aa, max <3000 aa for bacteria
    expect(result.min).toBeGreaterThan(20);
    expect(result.max).toBeLessThan(3000);
    // Average bacterial protein is 250-400 aa
    expect(result.avg).toBeGreaterThan(200);
    expect(result.avg).toBeLessThan(500);
  });

  test('gene lengths are positive and within bacterial range', async ({ page }) => {
    const result = await page.evaluate(() => {
      const lens = genes.map(g => g[F.LENGTH]);
      const min = Math.min(...lens);
      const max = Math.max(...lens);
      return { min, max };
    });

    expect(result.min).toBeGreaterThan(0);
    // Max gene length in E. coli should be <15000 bp
    expect(result.max).toBeLessThan(15000);
  });

  test('tree distances are correct Jaccard values (0 to 1)', async ({ page }) => {
    await page.click('.tab-btn[data-tab="tree"]');
    await page.waitForSelector('.tree-leaf', { timeout: 10000 });

    const result = await page.evaluate(() => {
      if (!treeData) return null;
      const dists = treeData.linkage.map(r => r[2]);
      return {
        min: Math.min(...dists),
        max: Math.max(...dists),
        count: dists.length,
      };
    });

    expect(result).not.toBeNull();
    expect(result.min).toBeGreaterThan(0);
    expect(result.max).toBeLessThanOrEqual(1.0);
    // Should have n-1 = 35 linkage rows for 36 genomes
    expect(result.count).toBe(EXPECTED.nTotalGenomes - 1);
  });

  test('cluster UMAP embeddings have reasonable spread', async ({ page }) => {
    await page.click('.tab-btn[data-tab="cluster"]');
    await page.waitForSelector('#cluster-canvas', { timeout: 10000 });
    await page.waitForTimeout(500);

    const result = await page.evaluate(() => {
      if (!clusterData) return null;
      const xs = clusterData.features.x;
      const ys = clusterData.features.y;
      const xRange = Math.max(...xs) - Math.min(...xs);
      const yRange = Math.max(...ys) - Math.min(...ys);
      return { xRange, yRange, nPoints: xs.length };
    });

    expect(result).not.toBeNull();
    expect(result.nPoints).toBe(EXPECTED.totalGenes);
    // UMAP should produce meaningful spread (not all collapsed to a point)
    expect(result.xRange).toBeGreaterThan(5);
    expect(result.yRange).toBeGreaterThan(5);
  });
});

// =============================================================================
// METABOLIC MAP TAB - FUNCTIONALITY
// =============================================================================
test.describe('Metabolic Map Tab - Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#kpi-bar .kpi-stat');
    await page.click('.tab-btn[data-tab="metabolic"]');
    await page.waitForSelector('#metabolic-container svg', { timeout: 15000 });
  });

  test('Metabolic Map tab loads and shows Escher SVG', async ({ page }) => {
    await expect(page.locator('#tab-metabolic')).toHaveClass(/active/);
    const svg = page.locator('#metabolic-container svg');
    await expect(svg).toBeVisible();
  });

  test('map selector has Full and Core options', async ({ page }) => {
    const select = page.locator('#metabolic-map-select');
    const options = select.locator('option');
    await expect(options).toHaveCount(2);
    await expect(options.nth(0)).toHaveText('Global Metabolism');
    await expect(options.nth(1)).toHaveText('Core Metabolism');
  });

  test('color-by selector has all 6 options', async ({ page }) => {
    const select = page.locator('#metabolic-color-by');
    const options = select.locator('option');
    await expect(options).toHaveCount(6);
  });

  test('switching to Core Metabolism loads different map', async ({ page }) => {
    await page.selectOption('#metabolic-map-select', 'core');
    await page.waitForTimeout(2000);
    const stats = await page.locator('#metabolic-stats').textContent();
    expect(stats).toContain('119');
    expect(stats).toContain('201');
  });

  test('changing color mode updates legend', async ({ page }) => {
    const legendBefore = await page.locator('#metabolic-legend').textContent();
    await page.selectOption('#metabolic-color-by', 'class_rich');
    await page.waitForTimeout(1000);
    const legendAfter = await page.locator('#metabolic-legend').textContent();
    expect(legendAfter).not.toBe(legendBefore);
    expect(legendAfter).toContain('Blocked');
    expect(legendAfter).toContain('Essential');
  });

  test('clicking a reaction shows detail in sidebar', async ({ page }) => {
    await page.waitForTimeout(600); // wait for click handler registration
    const clicked = await page.evaluate(() => {
      const svg = document.querySelector('#metabolic-container svg');
      const texts = svg.querySelectorAll('text');
      const rxnText = Array.from(texts).find(t => t.textContent.match(/^rxn\d/));
      if (rxnText) {
        const rxnGroup = rxnText.closest('.reaction');
        if (rxnGroup) {
          rxnGroup.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          return rxnText.textContent;
        }
      }
      return null;
    });
    expect(clicked).toBeTruthy();
    await page.waitForTimeout(200);
    const detail = await page.locator('#metabolic-rxn-detail').textContent();
    expect(detail).toContain(clicked);
  });
});

// =============================================================================
// METABOLIC MAP TAB - DATA CORRECTNESS
// =============================================================================
test.describe('Metabolic Map Tab - Data Correctness', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#kpi-bar .kpi-stat');
    await page.click('.tab-btn[data-tab="metabolic"]');
    await page.waitForSelector('#metabolic-container svg', { timeout: 15000 });
  });

  test('stats show correct total reaction count', async ({ page }) => {
    const stats = await page.locator('#metabolic-stats').textContent();
    expect(stats).toContain('1279');
  });

  test('Global Metabolism map shows correct coverage', async ({ page }) => {
    const stats = await page.locator('#metabolic-stats').textContent();
    expect(stats).toContain('508');
    expect(stats).toContain('759');
  });

  test('SVG contains reaction elements', async ({ page }) => {
    // Wait for Escher to render reaction groups (may take a moment after SVG appears)
    await page.waitForSelector('#metabolic-container svg .reaction', { timeout: 10000 });
    const rxnCount = await page.evaluate(() => {
      const svg = document.querySelector('#metabolic-container svg');
      return svg.querySelectorAll('.reaction').length;
    });
    expect(rxnCount).toBeGreaterThan(100);
  });

  test('toolbar shows map name and reaction count', async ({ page }) => {
    const toolbar = await page.locator('#metabolic-toolbar').textContent();
    expect(toolbar).toContain('Global Metabolism');
    expect(toolbar).toContain('1279');
  });

  test('conservation legend has correct categories', async ({ page }) => {
    const legend = await page.locator('#metabolic-legend').textContent();
    expect(legend).toContain('Absent');
    expect(legend).toContain('Low');
    expect(legend).toContain('High');
  });
});

// =============================================================================
// TAB SWITCHING
// =============================================================================
test.describe('Tab Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('#kpi-bar .kpi-stat');
  });

  test('can switch between all 4 tabs', async ({ page }) => {
    // Start on Tracks
    await expect(page.locator('#tab-tracks')).toHaveClass(/active/);

    // Switch to Tree
    await page.click('.tab-btn[data-tab="tree"]');
    await expect(page.locator('#tab-tree')).toHaveClass(/active/);
    await expect(page.locator('#tab-tracks')).not.toHaveClass(/active/);

    // Switch to Cluster
    await page.click('.tab-btn[data-tab="cluster"]');
    await expect(page.locator('#tab-cluster')).toHaveClass(/active/);
    await expect(page.locator('#tab-tree')).not.toHaveClass(/active/);

    // Switch to Metabolic Map
    await page.click('.tab-btn[data-tab="metabolic"]');
    await expect(page.locator('#tab-metabolic')).toHaveClass(/active/);
    await expect(page.locator('#tab-cluster')).not.toHaveClass(/active/);

    // Switch back to Tracks
    await page.click('.tab-btn[data-tab="tracks"]');
    await expect(page.locator('#tab-tracks')).toHaveClass(/active/);
  });

  test('KPI bar persists across tab switches', async ({ page }) => {
    const kpiBefore = await page.locator('#kpi-bar').textContent();

    await page.click('.tab-btn[data-tab="tree"]');
    await page.waitForTimeout(200);
    const kpiTree = await page.locator('#kpi-bar').textContent();
    expect(kpiTree).toBe(kpiBefore);

    await page.click('.tab-btn[data-tab="cluster"]');
    await page.waitForTimeout(200);
    const kpiCluster = await page.locator('#kpi-bar').textContent();
    expect(kpiCluster).toBe(kpiBefore);
  });
});
