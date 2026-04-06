"""Puppeteer baseline runner -- calls the Node.js script."""

from __future__ import annotations

import base64
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

SCRIPT_PATH = Path(__file__).parent / "puppeteer_baseline.js"


@dataclass(slots=True)
class PuppeteerResult:
    screenshot_png: bytes
    text: str
    puppeteer_version: str


def run_puppeteer_baseline() -> PuppeteerResult:
    """Launch vanilla Puppeteer via Node.js, visit CreepJS, capture results."""
    logger.info("Running Puppeteer baseline via Node.js")
    result = subprocess.run(
        ["node", str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        logger.error("Puppeteer script stderr: %s", result.stderr)
        raise RuntimeError(f"Puppeteer baseline failed: {result.stderr}")

    data = json.loads(result.stdout)
    logger.info("Puppeteer baseline complete (version: %s)", data["puppeteer_version"])
    return PuppeteerResult(
        screenshot_png=base64.b64decode(data["screenshot_b64"]),
        text=data["text"],
        puppeteer_version=data["puppeteer_version"],
    )
