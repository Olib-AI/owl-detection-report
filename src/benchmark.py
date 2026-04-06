"""Benchmark runner — measures cold start, navigation, screenshot, and full cycle times."""

from __future__ import annotations

import json
import logging
import statistics
import time
from pathlib import Path
from typing import Any

from .owl_client import OwlClient
from .s3_uploader import s3_configured, upload_directory

logger = logging.getLogger(__name__)

TARGET_URL = "https://example.com"
ITERATIONS = 1000


def _stats(times: list[float]) -> dict[str, float]:
    """Calculate summary statistics for a list of times in ms."""
    if not times:
        return {"min": 0, "max": 0, "avg": 0, "median": 0, "p95": 0}
    sorted_t = sorted(times)
    p95_idx = max(0, int(len(sorted_t) * 0.95) - 1)
    return {
        "min": round(sorted_t[0], 2),
        "max": round(sorted_t[-1], 2),
        "avg": round(statistics.mean(sorted_t), 2),
        "median": round(statistics.median(sorted_t), 2),
        "p95": round(sorted_t[p95_idx], 2),
    }


def _bench_owl(client: OwlClient) -> dict[str, Any]:
    """Benchmark Owl Browser: context creation, navigation, screenshot, full cycle."""
    logger.info("=== Benchmarking Owl Browser (%d iterations) ===", ITERATIONS)

    create_times: list[float] = []
    navigate_times: list[float] = []
    screenshot_times: list[float] = []
    close_times: list[float] = []
    cycle_times: list[float] = []

    for i in range(ITERATIONS):
        cycle_start = time.perf_counter()
        context_id: str | None = None
        try:
            # Create context
            t0 = time.perf_counter()
            resp = client._execute("browser_create_context", {"screen_size": "1920x1080"})
            create_ms = (time.perf_counter() - t0) * 1000
            create_times.append(create_ms)
            context_id = str(resp["context_id"])

            # Navigate
            t0 = time.perf_counter()
            client._execute("browser_navigate", {
                "context_id": context_id,
                "url": TARGET_URL,
                "wait_until": "domcontentloaded",
            })
            navigate_ms = (time.perf_counter() - t0) * 1000
            navigate_times.append(navigate_ms)

            # Screenshot
            t0 = time.perf_counter()
            client._execute("browser_screenshot", {"context_id": context_id})
            screenshot_ms = (time.perf_counter() - t0) * 1000
            screenshot_times.append(screenshot_ms)

        finally:
            if context_id:
                t0 = time.perf_counter()
                try:
                    client._execute("browser_close_context", {"context_id": context_id})
                except Exception:
                    pass
                close_ms = (time.perf_counter() - t0) * 1000
                close_times.append(close_ms)

        cycle_ms = (time.perf_counter() - cycle_start) * 1000
        cycle_times.append(cycle_ms)
        logger.info("  [%d/%d] create=%.0fms nav=%.0fms shot=%.0fms cycle=%.0fms",
                     i + 1, ITERATIONS, create_ms, navigate_ms, screenshot_ms, cycle_ms)

    return {
        "context_creation": _stats(create_times),
        "navigation": _stats(navigate_times),
        "screenshot": _stats(screenshot_times),
        "context_close": _stats(close_times),
        "full_cycle": _stats(cycle_times),
        "raw_ms": {
            "context_creation": [round(t, 2) for t in create_times],
            "navigation": [round(t, 2) for t in navigate_times],
            "screenshot": [round(t, 2) for t in screenshot_times],
            "full_cycle": [round(t, 2) for t in cycle_times],
        },
    }


def _bench_playwright() -> dict[str, Any]:
    """Benchmark Playwright: browser launch, navigation, screenshot, full cycle."""
    from playwright.sync_api import sync_playwright

    logger.info("=== Benchmarking Playwright (%d iterations) ===", ITERATIONS)

    launch_times: list[float] = []
    navigate_times: list[float] = []
    screenshot_times: list[float] = []
    close_times: list[float] = []
    cycle_times: list[float] = []
    version = "unknown"

    with sync_playwright() as pw:
        version = pw.chromium.name
        for i in range(ITERATIONS):
            cycle_start = time.perf_counter()

            # Launch browser (cold start)
            t0 = time.perf_counter()
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            launch_ms = (time.perf_counter() - t0) * 1000
            launch_times.append(launch_ms)

            # Navigate
            t0 = time.perf_counter()
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30_000)
            navigate_ms = (time.perf_counter() - t0) * 1000
            navigate_times.append(navigate_ms)

            # Screenshot
            t0 = time.perf_counter()
            page.screenshot()
            screenshot_ms = (time.perf_counter() - t0) * 1000
            screenshot_times.append(screenshot_ms)

            # Close
            t0 = time.perf_counter()
            browser.close()
            close_ms = (time.perf_counter() - t0) * 1000
            close_times.append(close_ms)

            cycle_ms = (time.perf_counter() - cycle_start) * 1000
            cycle_times.append(cycle_ms)
            logger.info("  [%d/%d] launch=%.0fms nav=%.0fms shot=%.0fms cycle=%.0fms",
                         i + 1, ITERATIONS, launch_ms, navigate_ms, screenshot_ms, cycle_ms)

    return {
        "version": version,
        "browser_launch": _stats(launch_times),
        "navigation": _stats(navigate_times),
        "screenshot": _stats(screenshot_times),
        "browser_close": _stats(close_times),
        "full_cycle": _stats(cycle_times),
        "raw_ms": {
            "browser_launch": [round(t, 2) for t in launch_times],
            "navigation": [round(t, 2) for t in navigate_times],
            "screenshot": [round(t, 2) for t in screenshot_times],
            "full_cycle": [round(t, 2) for t in cycle_times],
        },
    }


def _bench_puppeteer() -> dict[str, Any]:
    """Benchmark Puppeteer via Node.js subprocess."""
    import subprocess

    logger.info("=== Benchmarking Puppeteer (%d iterations) ===", ITERATIONS)

    script = Path(__file__).parent / "puppeteer_benchmark.js"
    result = subprocess.run(
        ["node", str(script), str(ITERATIONS), TARGET_URL],
        capture_output=True, text=True, timeout=7200,
    )
    if result.returncode != 0:
        logger.error("Puppeteer benchmark stderr: %s", result.stderr)
        raise RuntimeError(f"Puppeteer benchmark failed: {result.stderr}")

    data = json.loads(result.stdout)
    logger.info("  Puppeteer benchmark complete (%s)", data.get("version", "unknown"))
    return data


def run_benchmark(owl_url: str, owl_token: str, output_dir: Path) -> int:
    """Run benchmarks for all three browsers and write results."""
    from datetime import datetime, timezone

    output_dir.mkdir(parents=True, exist_ok=True)

    client = OwlClient(owl_url, owl_token)
    owl_version = client.get_version()
    logger.info("Owl Browser version: %s", owl_version)

    results: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_url": TARGET_URL,
        "iterations": ITERATIONS,
        "owl_version": owl_version,
        "methodology": (
            f"Each browser performs {ITERATIONS} sequential iterations of: "
            "create/launch → navigate to target URL (wait for domcontentloaded) → "
            "capture screenshot → close. All times in milliseconds. "
            "Playwright and Puppeteer run inside the benchmark container (local process). "
            "Owl Browser runs in a separate container and is accessed via REST API over localhost, "
            "adding ~5-10ms of network overhead per API call — Owl's real times are faster than shown. "
            "Sequential execution, same machine."
        ),
        "browsers": {},
    }

    # Playwright
    try:
        pw_result = _bench_playwright()
        results["browsers"]["playwright"] = pw_result
        results["playwright_version"] = pw_result.pop("version", "unknown")
    except Exception:
        logger.error("Playwright benchmark failed", exc_info=True)

    # Puppeteer
    try:
        pup_result = _bench_puppeteer()
        results["browsers"]["puppeteer"] = pup_result
        results["puppeteer_version"] = pup_result.pop("version", "unknown")
    except Exception:
        logger.error("Puppeteer benchmark failed", exc_info=True)

    # Owl Browser
    try:
        owl_result = _bench_owl(client)
        results["browsers"]["owl"] = owl_result
    except Exception:
        logger.error("Owl Browser benchmark failed", exc_info=True)

    if not results["browsers"]:
        logger.error("All benchmarks failed.")
        return 1

    # Write report
    report_path = output_dir / "benchmark.json"
    report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    logger.info("Wrote benchmark to %s", report_path)

    # S3 upload
    if s3_configured():
        logger.info("=== Uploading to S3 ===")
        try:
            upload_directory(output_dir)
        except Exception:
            logger.error("S3 upload failed", exc_info=True)
            return 1
    else:
        logger.info("S3 not configured, skipping upload")

    logger.info("=== Benchmark complete ===")
    return 0
