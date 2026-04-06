"""Stealth plugin runners for Playwright and Puppeteer — via Node.js scripts."""

from __future__ import annotations

import base64
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class StealthResult:
    screenshot_png: bytes
    text: str
    version: str


def run_playwright_stealth() -> StealthResult:
    """Run Playwright + stealth plugin via Node.js."""
    script = Path(__file__).parent / "playwright_stealth_baseline.js"
    logger.info("Running Playwright + stealth plugin via Node.js")
    result = subprocess.run(
        ["node", str(script)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        logger.error("Playwright stealth stderr: %s", result.stderr)
        raise RuntimeError(f"Playwright stealth failed: {result.stderr}")

    data = json.loads(result.stdout)
    logger.info("Playwright stealth complete (version: %s)", data["playwright_version"])
    return StealthResult(
        screenshot_png=base64.b64decode(data["screenshot_b64"]),
        text=data["text"],
        version=data["playwright_version"],
    )


def run_puppeteer_stealth() -> StealthResult:
    """Run Puppeteer + stealth plugin via Node.js."""
    script = Path(__file__).parent / "puppeteer_stealth_baseline.js"
    logger.info("Running Puppeteer + stealth plugin via Node.js")
    result = subprocess.run(
        ["node", str(script)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        logger.error("Puppeteer stealth stderr: %s", result.stderr)
        raise RuntimeError(f"Puppeteer stealth failed: {result.stderr}")

    data = json.loads(result.stdout)
    logger.info("Puppeteer stealth complete (version: %s)", data["puppeteer_version"])
    return StealthResult(
        screenshot_png=base64.b64decode(data["screenshot_b64"]),
        text=data["text"],
        version=data["puppeteer_version"],
    )
