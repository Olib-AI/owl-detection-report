/**
 * Puppeteer concurrency benchmark — spawn N browsers simultaneously.
 * Usage: node puppeteer_concurrency.js <sessions> <target_url>
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

async function runSession(executablePath, targetUrl) {
  let browser;
  try {
    let t0 = performance.now();
    browser = await puppeteer.launch({
      executablePath,
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--ignore-certificate-errors'],
    });
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });
    const launchMs = performance.now() - t0;

    t0 = performance.now();
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const navMs = performance.now() - t0;

    t0 = performance.now();
    await page.screenshot();
    const shotMs = performance.now() - t0;

    await browser.close();
    browser = null;

    return { success: true, launch: round2(launchMs), navigate: round2(navMs), screenshot: round2(shotMs) };
  } catch (err) {
    if (browser) { try { await browser.close(); } catch {} }
    return { success: false, error: err.message };
  }
}

(async () => {
  const sessions = parseInt(process.argv[2]) || 10;
  const targetUrl = process.argv[3] || 'https://example.com';
  const executablePath = findChromium();

  const tStart = performance.now();
  const promises = [];
  for (let i = 0; i < sessions; i++) {
    promises.push(runSession(executablePath, targetUrl));
  }
  const results = await Promise.all(promises);
  const totalMs = performance.now() - tStart;

  const succeeded = results.filter(r => r.success);
  const avgLaunch = succeeded.length ? succeeded.reduce((s, r) => s + r.launch, 0) / succeeded.length : 0;
  const avgNav = succeeded.length ? succeeded.reduce((s, r) => s + r.navigate, 0) / succeeded.length : 0;
  const avgShot = succeeded.length ? succeeded.reduce((s, r) => s + r.screenshot, 0) / succeeded.length : 0;

  const output = {
    sessions,
    succeeded: succeeded.length,
    failed: sessions - succeeded.length,
    total_time_ms: round2(totalMs),
    avg_launch_ms: round2(avgLaunch),
    avg_navigate_ms: round2(avgNav),
    avg_screenshot_ms: round2(avgShot),
  };

  process.stdout.write(JSON.stringify(output));
})();
