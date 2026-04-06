"""Build the structured JSON report."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .creepjs_parser import CreepJSResult

logger = logging.getLogger(__name__)


def result_to_dict(parsed: CreepJSResult, screenshot_path: str) -> dict[str, Any]:
    return {
        "screenshot": screenshot_path,
        **asdict(parsed),
    }


def build_report(
    profiles: dict[str, dict[str, Any]],
    owl_version: str = "unknown",
    playwright_version: str = "unknown",
    puppeteer_version: str = "unknown",
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "owl_version": owl_version,
        "playwright_version": playwright_version,
        "puppeteer_version": puppeteer_version,
        "profiles": profiles,
    }


def write_report(report: dict[str, Any], output_dir: Path) -> Path:
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    logger.info("Wrote report to %s", report_path)
    return report_path
