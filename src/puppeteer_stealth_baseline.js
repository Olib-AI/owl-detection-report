/**
 * Puppeteer + stealth plugin baseline runner.
 * Outputs JSON to stdout: { screenshot_b64, text, puppeteer_version }
 */

const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const { execSync } = require('child_process');

puppeteer.use(StealthPlugin());

const CREEPJS_URL = 'https://abrahamjuliot.github.io/creepjs/';
const WAIT_MS = 15000;

function findChromium() {
  try {
    const out = execSync('find /root/.cache/ms-playwright -name "chrome" -type f 2>/dev/null | head -1', { encoding: 'utf-8' }).trim();
    if (out) return out;
  } catch {}
  throw new Error('No Chromium binary found');
}

(async () => {
  const executablePath = findChromium();
  const browser = await puppeteer.launch({
    executablePath,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });

    await page.goto(CREEPJS_URL, { waitUntil: 'networkidle0', timeout: 60000 });
    await new Promise(resolve => setTimeout(resolve, WAIT_MS));

    const screenshot = await page.screenshot({ fullPage: true, encoding: 'base64' });
    const text = await page.evaluate(() => document.body.innerText);
    const version = await browser.version();

    process.stdout.write(JSON.stringify({ screenshot_b64: screenshot, text, puppeteer_version: version + ' + stealth' }));
  } finally {
    await browser.close();
  }
})();
