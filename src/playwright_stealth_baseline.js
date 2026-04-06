/**
 * Playwright + stealth plugin baseline runner.
 * Outputs JSON to stdout: { screenshot_b64, text, playwright_version }
 */

const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');

chromium.use(StealthPlugin());

const CREEPJS_URL = 'https://abrahamjuliot.github.io/creepjs/';
const WAIT_MS = 15000;

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });

    await page.goto(CREEPJS_URL, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(WAIT_MS);

    const screenshot = await page.screenshot({ fullPage: true });
    const text = await page.innerText('body');
    const version = browser.version();

    process.stdout.write(JSON.stringify({
      screenshot_b64: screenshot.toString('base64'),
      text,
      playwright_version: 'chromium ' + version + ' + stealth',
    }));
  } finally {
    await browser.close();
  }
})();
