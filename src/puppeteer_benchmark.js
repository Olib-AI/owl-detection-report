/**
 * Puppeteer benchmark — measures launch, navigation, screenshot, full cycle.
 * Usage: node puppeteer_benchmark.js <iterations> <target_url>
 * Outputs JSON to stdout.
 */

const puppeteer = require('puppeteer-core');
const { execSync } = require('child_process');

function findChromium() {
  try {
    const out = execSync('find /root/.cache/ms-playwright -name "chrome" -type f 2>/dev/null | head -1', { encoding: 'utf-8' }).trim();
    if (out) return out;
  } catch {}
  try {
    const out = execSync('find /root/.cache/puppeteer -name "chrome" -type f 2>/dev/null | head -1', { encoding: 'utf-8' }).trim();
    if (out) return out;
  } catch {}
  throw new Error('No Chromium binary found');
}

function round2(n) { return Math.round(n * 100) / 100; }

function stats(arr) {
  if (!arr.length) return { min: 0, max: 0, avg: 0, median: 0, p95: 0 };
  const sorted = [...arr].sort((a, b) => a - b);
  const p95Idx = Math.max(0, Math.ceil(sorted.length * 0.95) - 1);
  const sum = sorted.reduce((a, b) => a + b, 0);
  const mid = Math.floor(sorted.length / 2);
  const median = sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  return {
    min: round2(sorted[0]),
    max: round2(sorted[sorted.length - 1]),
    avg: round2(sum / sorted.length),
    median: round2(median),
    p95: round2(sorted[p95Idx]),
  };
}

(async () => {
  const iterations = parseInt(process.argv[2]) || 10;
  const targetUrl = process.argv[3] || 'https://example.com';
  const executablePath = findChromium();

  const launchTimes = [];
  const navTimes = [];
  const shotTimes = [];
  const closeTimes = [];
  const cycleTimes = [];
  let version = 'unknown';
  let errors = 0;
  const MAX_RETRIES = 3;

  for (let i = 0; i < iterations; i++) {
    let retries = 0;
    let success = false;

    while (retries < MAX_RETRIES && !success) {
      let browser;
      try {
        const cycleStart = performance.now();

        // Launch (cold start)
        let t0 = performance.now();
        browser = await puppeteer.launch({
          executablePath,
          headless: 'new',
          args: ['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors'],
        });
        const page = await browser.newPage();
        await page.setViewport({ width: 1920, height: 1080 });
        const launchMs = performance.now() - t0;

        if (i === 0 && retries === 0) version = await browser.version();

        // Navigate
        t0 = performance.now();
        await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
        const navMs = performance.now() - t0;

        // Screenshot
        t0 = performance.now();
        await page.screenshot();
        const shotMs = performance.now() - t0;

        // Close
        t0 = performance.now();
        await browser.close();
        browser = null;
        const closeMs = performance.now() - t0;

        const cycleMs = performance.now() - cycleStart;

        launchTimes.push(launchMs);
        navTimes.push(navMs);
        shotTimes.push(shotMs);
        closeTimes.push(closeMs);
        cycleTimes.push(cycleMs);
        success = true;
      } catch (err) {
        retries++;
        if (browser) {
          try { await browser.close(); } catch {}
        }
        if (retries >= MAX_RETRIES) {
          errors++;
          process.stderr.write(`Iteration ${i + 1}: failed after ${MAX_RETRIES} retries: ${err.message}\n`);
        }
      }
    }
  }

  const result = {
    version,
    completed: launchTimes.length,
    errors,
    browser_launch: stats(launchTimes),
    navigation: stats(navTimes),
    screenshot: stats(shotTimes),
    browser_close: stats(closeTimes),
    full_cycle: stats(cycleTimes),
    raw_ms: {
      browser_launch: launchTimes.map(round2),
      navigation: navTimes.map(round2),
      screenshot: shotTimes.map(round2),
      full_cycle: cycleTimes.map(round2),
    },
  };

  process.stdout.write(JSON.stringify(result));
})();
