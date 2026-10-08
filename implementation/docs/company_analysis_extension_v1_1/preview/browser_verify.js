/* Local browser behavior checks. Uses only the already installed Playwright. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES + '/playwright');
let base = process.argv[2];
const server = base ? null : http.createServer((request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const target = path.resolve(__dirname, '.' + pathname);
    if (!target.startsWith(__dirname + path.sep) || !fs.statSync(target).isFile()) throw new Error('Missing local file');
    const contentTypes = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.md': 'text/plain'};
    response.writeHead(200, {'Content-Type': contentTypes[path.extname(target)] || 'application/octet-stream'});
    response.end(fs.readFileSync(target));
  } catch {
    response.writeHead(404); response.end('Unavailable');
  }
});

(async () => {
  const executable = process.env.BROWSER_EXECUTABLE_PATH;
  let browser;
  const errors = [];
  try {
    if (server) {
      await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
      base = 'http://127.0.0.1:' + server.address().port;
    }
    browser = await chromium.launch({ headless: true, ...(executable ? { executablePath: executable } : {}) });
    const page = await browser.newPage();
    page.on('pageerror', error => errors.push(String(error)));
    for (const width of [1360, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(base + '/index.html');
      await page.waitForSelector('#quarterly-summary[data-status="AVAILABLE"]');
      assert.equal(await page.locator('main > section').count(), 10);
      assert.match(await page.locator('#quarterly-summary').innerText(), /2 \/ 4/);
      assert.match(await page.locator('#quarterly-summary').innerText(), /50%/);
      assert.match(await page.locator('#annual-summary').innerText(), /2 \/ 3/);
      assert.match(await page.locator('#annual-summary').innerText(), /66\.7%/);
      assert.equal(await page.locator('svg .baseline').count(), 2);
      assert.equal(await page.locator('.classification-axis').count(), 3);
      assert.ok(!(await page.locator('main').innerText()).match(/negative (count|rate)/i));
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.locator('#quarterly-chart a').first().click();
      assert.match(page.url(), /detail\.html\?kind=QUARTERLY&period=2025-Q1/);
      assert.match(await page.locator('#detail-content').innerText(), /10%/);
      await page.locator('#detail-evidence').click();
      assert.match(page.url(), /evidence\.html/);
      assert.match(await page.locator('#evidence-content').innerText(), /synthetic:prices-v1/);
      await page.goto(base + '/detail.html?view=full-chart');
      assert.match(await page.locator('#detail-content').innerText(), /not assembled/i);
      await page.goto(base + '/detail.html?view=thesis#quality');
      assert.equal(await page.locator('#quality').count(), 1);
      const localLinks = await page.locator('a[href]').evaluateAll(links => links.map(a => a.getAttribute('href')));
      assert.ok(localLinks.every(href => !/^(https?:|\/\/)/.test(href)));
    }
    // Currency must follow the validated projection, not unrelated company metadata.
    const sample = await page.evaluate(() => structuredClone(window.COMPANY_SAMPLE));
    const euro = structuredClone(sample);
    euro.company.currency = 'USD';
    euro.price_position.evidence.bindings.currency = 'EUR';
    await page.route('**/sample.js', route => route.fulfill({ contentType: 'text/javascript', body: 'window.COMPANY_SAMPLE = ' + JSON.stringify(euro) + ';' }));
    await page.goto(base + '/index.html');
    assert.equal(await page.locator('#price-position .metric-value').first().innerText(), 'EUR 100');
    await page.unroute('**/sample.js');
    // An unavailable projection must not retain numeric prices or a positive rate.
    sample.company.name = '<img src=x onerror="window.injected=true">';
    sample.price_position = {status: 'NOT_AVAILABLE', reason_codes: ['TEST_UNAVAILABLE'], values: {current_price: '100', historical_ath: '125'}, evidence: {}};
    for (const key of ['quarterly', 'annual']) sample[key] = {status: 'NOT_AVAILABLE', reason_codes: ['TEST_UNAVAILABLE'], bars: [{label: '<script>window.injected=true</script>', return_percent: '90'}], positive_rate_percent: '90', positive_count: 9, completed_count: 10};
    await page.route('**/sample.js', route => route.fulfill({ contentType: 'text/javascript', body: 'window.COMPANY_SAMPLE = ' + JSON.stringify(sample) + ';' }));
    await page.goto(base + '/index.html');
    assert.match(await page.locator('#company-name').innerText(), /<img/);
    assert.equal(await page.locator('#company-name img').count(), 0);
    assert.equal(await page.evaluate(() => window.injected), undefined);
    assert.match(await page.locator('#price-position').innerText(), /Unavailable/);
    assert.match(await page.locator('#data-stamp').innerText(), /Basis: Unavailable/);
    assert.match(await page.locator('#data-stamp').innerText(), /Actions receipt: Unavailable/);
    assert.ok(!(await page.locator('#price-position').innerText()).includes('$100'));
    assert.equal(await page.locator('#quarterly-chart svg').count(), 0);
    assert.ok(!(await page.locator('#quarterly-summary').innerText()).includes('90%'));
    assert.deepEqual(errors, []);
    console.log('PASS: desktop/mobile, 10 sections, independent axes, baseline bars, positive summaries, drill-down, evidence, honest full-chart state, local links, validated currency, unavailable clearing, text injection safety.');
  } finally {
    if (browser) await browser.close();
    if (server) await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
