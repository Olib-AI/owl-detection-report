"""Entry point for the detection report generator."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("owl-detection-report")

PROFILES = ["windows", "macos", "linux"]


def run_detection_report() -> int:
    """Generate the CreepJS detection comparison report."""
    from .baseline_runner import run_baseline
    from .puppeteer_runner import run_puppeteer_baseline
    from .creepjs_parser import parse_creepjs
    from .owl_client import OwlClient
    from .report_builder import build_report, write_report, result_to_dict
    from .screenshot import save_webp
    from .s3_uploader import s3_configured, upload_directory

    owl_url = os.environ.get("OWL_BROWSER_URL")
    owl_token = os.environ.get("OWL_BROWSER_TOKEN")
    output_dir = Path(os.environ.get("OUTPUT_DIR", "/output"))

    if not owl_url or not owl_token:
        logger.error("OWL_BROWSER_URL and OWL_BROWSER_TOKEN are required")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    shots_dir = output_dir / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Playwright baseline (once — same for all OS profiles)
    logger.info("=== Running Playwright baseline ===")
    playwright_parsed = None
    playwright_version = "unknown"
    try:
        pw = run_baseline()
        playwright_version = pw.playwright_version
        save_webp(pw.screenshot_png, shots_dir / "playwright.webp")
        playwright_parsed = result_to_dict(parse_creepjs(pw.text), "screenshots/playwright.webp")
        logger.info("Playwright baseline complete (engine: %s)", playwright_version)
    except Exception:
        logger.error("Playwright baseline failed", exc_info=True)

    # Step 2: Puppeteer baseline (once)
    logger.info("=== Running Puppeteer baseline ===")
    puppeteer_parsed = None
    puppeteer_version = "unknown"
    try:
        pup = run_puppeteer_baseline()
        puppeteer_version = pup.puppeteer_version
        save_webp(pup.screenshot_png, shots_dir / "puppeteer.webp")
        puppeteer_parsed = result_to_dict(parse_creepjs(pup.text), "screenshots/puppeteer.webp")
        logger.info("Puppeteer baseline complete (version: %s)", puppeteer_version)
    except Exception:
        logger.error("Puppeteer baseline failed", exc_info=True)

    # Step 3: Owl Browser version + per-OS profiles
    client = OwlClient(owl_url, owl_token)
    owl_version = client.get_version()
    logger.info("Owl Browser version: %s", owl_version)

    profiles: dict[str, dict[str, Any]] = {}

    for profile_os in PROFILES:
        logger.info("--- Owl Browser: %s ---", profile_os)
        profile_data: dict[str, Any] = {}

        try:
            result = client.run_creepjs(profile_os)
            shot_name = f"owl-{profile_os}.webp"
            save_webp(result.screenshot_png, shots_dir / shot_name)
            profile_data["owl"] = result_to_dict(parse_creepjs(result.text), f"screenshots/{shot_name}")
        except Exception:
            logger.error("Failed Owl run for %s", profile_os, exc_info=True)

        # Baselines are identical for all OS profiles
        if playwright_parsed is not None:
            profile_data["playwright"] = playwright_parsed
        if puppeteer_parsed is not None:
            profile_data["puppeteer"] = puppeteer_parsed

        if profile_data:
            profiles[profile_os] = profile_data

    if not profiles:
        logger.error("No profiles completed successfully. Aborting.")
        return 1

    # Step 4: Write report
    logger.info("=== Building report ===")
    report = build_report(
        profiles=profiles,
        owl_version=owl_version,
        playwright_version=playwright_version,
        puppeteer_version=puppeteer_version,
    )
    write_report(report, output_dir)

    # Step 5: Optional S3 upload
    if s3_configured():
        logger.info("=== Uploading to S3 ===")
        try:
            upload_directory(output_dir)
        except Exception:
            logger.error("S3 upload failed", exc_info=True)
            return 1
    else:
        logger.info("S3 not configured, skipping upload")

    logger.info("=== Done ===")
    return 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"

    if mode == "--benchmark":
        from .benchmark import run_benchmark

        owl_url = os.environ.get("OWL_BROWSER_URL")
        owl_token = os.environ.get("OWL_BROWSER_TOKEN")
        output_dir = Path(os.environ.get("OUTPUT_DIR", "/output"))

        if not owl_url or not owl_token:
            logger.error("OWL_BROWSER_URL and OWL_BROWSER_TOKEN are required")
            return 1

        return run_benchmark(owl_url, owl_token, output_dir)
    else:
        return run_detection_report()


if __name__ == "__main__":
    sys.exit(main())
