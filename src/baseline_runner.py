"""Playwright baseline runner -- vanilla Chromium, no stealth."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

CREEPJS_URL = "https://abrahamjuliot.github.io/creepjs/"
WAIT_MS = 15_000


@dataclass(slots=True)
class BaselineResult:
    screenshot_png: bytes
    text: str
    playwright_version: str


def run_baseline() -> BaselineResult:
    """Launch vanilla Playwright Chromium, visit CreepJS, capture results."""
    with sync_playwright() as pw:
        version = pw.chromium.name
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            logger.info("Navigating baseline Playwright to CreepJS")
            page.goto(CREEPJS_URL, wait_until="networkidle", timeout=60_000)

            logger.info("Waiting %dms for CreepJS computation", WAIT_MS)
            page.wait_for_timeout(WAIT_MS)

            screenshot_png = page.screenshot(full_page=True)
            text = page.inner_text("body")

            return BaselineResult(
                screenshot_png=screenshot_png,
                text=text,
                playwright_version=version,
            )
        finally:
            browser.close()
            logger.info("Closed baseline browser")
