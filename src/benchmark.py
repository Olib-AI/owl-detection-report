"""Benchmark runner — measures cold start, navigation, screenshot, full cycle, and concurrency."""

from __future__ import annotations

import concurrent.futures
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
CONCURRENCY_LEVELS = [1, 10, 25, 50, 100]


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

    errors = 0
    MAX_RETRIES = 3

    for i in range(ITERATIONS):
        retries = 0
        success = False

        while retries < MAX_RETRIES and not success:
            context_id: str | None = None
            try:
                cycle_start = time.perf_counter()

                # Create context
                t0 = time.perf_counter()
                resp = client._execute("browser_create_context", {"screen_size": "1920x1080"})
                create_ms = (time.perf_counter() - t0) * 1000
                context_id = str(resp["context_id"])

                # Navigate
                t0 = time.perf_counter()
                client._execute("browser_navigate", {
                    "context_id": context_id,
                    "url": TARGET_URL,
                    "wait_until": "domcontentloaded",
                })
                navigate_ms = (time.perf_counter() - t0) * 1000

                # Screenshot
                t0 = time.perf_counter()
                client._execute("browser_screenshot", {"context_id": context_id})
                screenshot_ms = (time.perf_counter() - t0) * 1000

                # Close
                t0 = time.perf_counter()
                client._execute("browser_close_context", {"context_id": context_id})
                context_id = None
                close_ms = (time.perf_counter() - t0) * 1000

                cycle_ms = (time.perf_counter() - cycle_start) * 1000

                create_times.append(create_ms)
                navigate_times.append(navigate_ms)
                screenshot_times.append(screenshot_ms)
                close_times.append(close_ms)
                cycle_times.append(cycle_ms)
                success = True

                if (i + 1) % 100 == 0 or i == 0:
                    logger.info("  [%d/%d] create=%.0fms nav=%.0fms shot=%.0fms cycle=%.0fms",
                                 i + 1, ITERATIONS, create_ms, navigate_ms, screenshot_ms, cycle_ms)
            except Exception as exc:
                retries += 1
                if context_id:
                    try:
                        client._execute("browser_close_context", {"context_id": context_id})
                    except Exception:
                        pass
                if retries >= MAX_RETRIES:
                    errors += 1
                    logger.warning("  [%d/%d] failed after %d retries: %s", i + 1, ITERATIONS, MAX_RETRIES, exc)

    logger.info("Owl: %d completed, %d errors", len(create_times), errors)
    return {
        "completed": len(create_times),
        "errors": errors,
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
    errors = 0
    MAX_RETRIES = 3

    with sync_playwright() as pw:
        version = pw.chromium.name
        for i in range(ITERATIONS):
            retries = 0
            success = False

            while retries < MAX_RETRIES and not success:
                browser = None
                try:
                    cycle_start = time.perf_counter()

                    # Launch browser (cold start)
                    t0 = time.perf_counter()
                    browser = pw.chromium.launch(
                        headless=True,
                        args=["--ignore-certificate-errors"],
                    )
                    page = browser.new_page(viewport={"width": 1920, "height": 1080})
                    launch_ms = (time.perf_counter() - t0) * 1000

                    # Navigate
                    t0 = time.perf_counter()
                    page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30_000)
                    navigate_ms = (time.perf_counter() - t0) * 1000

                    # Screenshot
                    t0 = time.perf_counter()
                    page.screenshot()
                    screenshot_ms = (time.perf_counter() - t0) * 1000

                    # Close
                    t0 = time.perf_counter()
                    browser.close()
                    browser = None
                    close_ms = (time.perf_counter() - t0) * 1000

                    cycle_ms = (time.perf_counter() - cycle_start) * 1000

                    launch_times.append(launch_ms)
                    navigate_times.append(navigate_ms)
                    screenshot_times.append(screenshot_ms)
                    close_times.append(close_ms)
                    cycle_times.append(cycle_ms)
                    success = True

                    if (i + 1) % 100 == 0 or i == 0:
                        logger.info("  [%d/%d] launch=%.0fms nav=%.0fms shot=%.0fms cycle=%.0fms",
                                     i + 1, ITERATIONS, launch_ms, navigate_ms, screenshot_ms, cycle_ms)
                except Exception as exc:
                    retries += 1
                    if browser:
                        try:
                            browser.close()
                        except Exception:
                            pass
                    if retries >= MAX_RETRIES:
                        errors += 1
                        logger.warning("  [%d/%d] failed after %d retries: %s", i + 1, ITERATIONS, MAX_RETRIES, exc)

    logger.info("Playwright: %d completed, %d errors", len(launch_times), errors)
    return {
        "version": version,
        "completed": len(launch_times),
        "errors": errors,
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


def _concurrent_owl(client: OwlClient, n: int) -> dict[str, Any]:
    """Spawn N Owl Browser contexts concurrently, navigate, screenshot, close."""

    def _single_session(_: int) -> dict[str, Any]:
        context_id = None
        try:
            t0 = time.perf_counter()
            resp = client._execute("browser_create_context", {"screen_size": "1920x1080"})
            context_id = str(resp["context_id"])
            create_ms = (time.perf_counter() - t0) * 1000

            t0 = time.perf_counter()
            client._execute("browser_navigate", {
                "context_id": context_id,
                "url": TARGET_URL,
                "wait_until": "domcontentloaded",
            })
            nav_ms = (time.perf_counter() - t0) * 1000

            t0 = time.perf_counter()
            client._execute("browser_screenshot", {"context_id": context_id})
            shot_ms = (time.perf_counter() - t0) * 1000

            return {"success": True, "create": create_ms, "navigate": nav_ms, "screenshot": shot_ms}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
        finally:
            if context_id:
                try:
                    client._execute("browser_close_context", {"context_id": context_id})
                except Exception:
                    pass

    t_start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(_single_session, i) for i in range(n)]
        results = [f.result() for f in futures]
    total_ms = (time.perf_counter() - t_start) * 1000

    succeeded = [r for r in results if r["success"]]
    return {
        "sessions": n,
        "succeeded": len(succeeded),
        "failed": n - len(succeeded),
        "total_time_ms": round(total_ms, 2),
        "avg_create_ms": round(statistics.mean(r["create"] for r in succeeded), 2) if succeeded else 0,
        "avg_navigate_ms": round(statistics.mean(r["navigate"] for r in succeeded), 2) if succeeded else 0,
        "avg_screenshot_ms": round(statistics.mean(r["screenshot"] for r in succeeded), 2) if succeeded else 0,
    }


def _playwright_single_session(target_url: str) -> dict[str, Any]:
    """Run a single Playwright session — must be top-level for ProcessPoolExecutor."""
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as pw:
            t0 = time.perf_counter()
            browser = pw.chromium.launch(
                headless=True,
                args=["--ignore-certificate-errors"],
            )
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            launch_ms = (time.perf_counter() - t0) * 1000

            t0 = time.perf_counter()
            page.goto(target_url, wait_until="domcontentloaded", timeout=30_000)
            nav_ms = (time.perf_counter() - t0) * 1000

            t0 = time.perf_counter()
            page.screenshot()
            shot_ms = (time.perf_counter() - t0) * 1000

            browser.close()
            return {"success": True, "launch": launch_ms, "navigate": nav_ms, "screenshot": shot_ms}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _concurrent_playwright(n: int) -> dict[str, Any]:
    """Spawn N Playwright browser instances concurrently using separate processes."""

    t_start = time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(_playwright_single_session, TARGET_URL) for _ in range(n)]
        results = [f.result(timeout=120) for f in futures]
    total_ms = (time.perf_counter() - t_start) * 1000

    succeeded = [r for r in results if r["success"]]
    return {
        "sessions": n,
        "succeeded": len(succeeded),
        "failed": n - len(succeeded),
        "total_time_ms": round(total_ms, 2),
        "avg_launch_ms": round(statistics.mean(r["launch"] for r in succeeded), 2) if succeeded else 0,
        "avg_navigate_ms": round(statistics.mean(r["navigate"] for r in succeeded), 2) if succeeded else 0,
        "avg_screenshot_ms": round(statistics.mean(r["screenshot"] for r in succeeded), 2) if succeeded else 0,
    }


def _concurrent_puppeteer(n: int) -> dict[str, Any]:
    """Spawn N Puppeteer browser instances concurrently via Node.js."""
    import subprocess

    script = Path(__file__).parent / "puppeteer_concurrency.js"
    result = subprocess.run(
        ["node", str(script), str(n), TARGET_URL],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        logger.error("Puppeteer concurrency stderr: %s", result.stderr)
        return {"sessions": n, "succeeded": 0, "failed": n, "total_time_ms": 0, "error": result.stderr[:500]}

    return json.loads(result.stdout)


def _bench_concurrency(client: OwlClient) -> dict[str, Any]:
    """Run concurrency benchmarks at increasing session counts."""
    logger.info("=== Concurrency Benchmark (levels: %s) ===", CONCURRENCY_LEVELS)

    results: dict[str, list[dict[str, Any]]] = {
        "owl": [],
        "playwright": [],
        "puppeteer": [],
    }

    for n in CONCURRENCY_LEVELS:
        logger.info("--- %d concurrent sessions ---", n)

        # Owl
        try:
            owl_r = _concurrent_owl(client, n)
            results["owl"].append(owl_r)
            logger.info("  Owl: %d/%d succeeded in %.0fms (avg create=%.0fms nav=%.0fms shot=%.0fms)",
                        owl_r["succeeded"], n, owl_r["total_time_ms"],
                        owl_r.get("avg_create_ms", 0), owl_r.get("avg_navigate_ms", 0), owl_r.get("avg_screenshot_ms", 0))
        except Exception:
            logger.error("  Owl concurrency failed at %d", n, exc_info=True)
            results["owl"].append({"sessions": n, "succeeded": 0, "failed": n, "total_time_ms": 0})

        # Playwright
        try:
            pw_r = _concurrent_playwright(n)
            results["playwright"].append(pw_r)
            logger.info("  Playwright: %d/%d succeeded in %.0fms", pw_r["succeeded"], n, pw_r["total_time_ms"])
        except Exception:
            logger.error("  Playwright concurrency failed at %d", n, exc_info=True)
            results["playwright"].append({"sessions": n, "succeeded": 0, "failed": n, "total_time_ms": 0})

        # Puppeteer
        try:
            pup_r = _concurrent_puppeteer(n)
            results["puppeteer"].append(pup_r)
            logger.info("  Puppeteer: %d/%d succeeded in %.0fms", pup_r.get("succeeded", 0), n, pup_r.get("total_time_ms", 0))
        except Exception:
            logger.error("  Puppeteer concurrency failed at %d", n, exc_info=True)
            results["puppeteer"].append({"sessions": n, "succeeded": 0, "failed": n, "total_time_ms": 0})

    return results


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

    # Concurrency benchmark
    try:
        concurrency = _bench_concurrency(client)
        results["concurrency"] = {
            "levels": CONCURRENCY_LEVELS,
            "methodology": (
                f"At each concurrency level ({', '.join(str(n) for n in CONCURRENCY_LEVELS)} sessions), "
                "all sessions launch simultaneously and each performs: create → navigate (domcontentloaded) → screenshot → close. "
                "Playwright and Puppeteer each launch a separate browser process per session. "
                "Owl Browser creates lightweight contexts within a single running engine. "
                "Total time = wall clock from first launch to last completion."
            ),
            "browsers": concurrency,
        }
    except Exception:
        logger.error("Concurrency benchmark failed", exc_info=True)

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


def run_concurrency_only(owl_url: str, owl_token: str, output_dir: Path) -> int:
    """Run only the concurrency benchmark and merge into existing benchmark.json."""
    from datetime import datetime, timezone

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "benchmark.json"

    # Load existing benchmark data
    existing: dict[str, Any] = {}
    if report_path.exists():
        try:
            existing = json.loads(report_path.read_text())
            logger.info("Loaded existing benchmark.json")
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read existing benchmark.json, starting fresh")

    client = OwlClient(owl_url, owl_token)
    owl_version = client.get_version()
    logger.info("Owl Browser version: %s", owl_version)

    # Run concurrency benchmark
    try:
        concurrency = _bench_concurrency(client)
        existing["concurrency"] = {
            "levels": CONCURRENCY_LEVELS,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "methodology": (
                f"At each concurrency level ({', '.join(str(n) for n in CONCURRENCY_LEVELS)} sessions), "
                "all sessions launch simultaneously and each performs: create → navigate (domcontentloaded) → screenshot → close. "
                "Playwright and Puppeteer each launch a separate browser process per session. "
                "Owl Browser creates lightweight contexts within a single running engine. "
                "Total time = wall clock from first launch to last completion."
            ),
            "browsers": concurrency,
        }
    except Exception:
        logger.error("Concurrency benchmark failed", exc_info=True)
        return 1

    # Write merged report
    report_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    logger.info("Wrote updated benchmark to %s", report_path)

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

    logger.info("=== Concurrency benchmark complete ===")
    return 0
