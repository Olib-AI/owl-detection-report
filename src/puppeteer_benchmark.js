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

  for (let i = 0; i < iterations; i++) {
    const cycleStart = performance.now();

    // Launch (cold start)
    let t0 = performance.now();
    const browser = await puppeteer.launch({
      executablePath,
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors'],
    });
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });
    const launchMs = performance.now() - t0;
    launchTimes.push(launchMs);

    if (i === 0) version = await browser.version();

    // Navigate
    t0 = performance.now();
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const navMs = performance.now() - t0;
    navTimes.push(navMs);

    // Screenshot
    t0 = performance.now();
    await page.screenshot();
    const shotMs = performance.now() - t0;
    shotTimes.push(shotMs);

    // Close
    t0 = performance.now();
    await browser.close();
    const closeMs = performance.now() - t0;
    closeTimes.push(closeMs);

    const cycleMs = performance.now() - cycleStart;
    cycleTimes.push(cycleMs);
  }

  const result = {
    version,
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
