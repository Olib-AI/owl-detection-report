"""Parse CreepJS detection results from page text output."""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CreepJSResult:
    fp_id: str
    like_headless: str
    headless: str
    stealth: str
    gpu_vendor: str
    gpu_renderer: str
    user_agent: str
    platform: str
    fonts_loaded: str
    devices_count: str
    worker_confidence: str
    # Fingerprint hashes — these prove spoofing works
    canvas_hash: str
    webgl_hash: str
    audio_hash: str
    fonts_hash: str
    domrect_hash: str
    svgrect_hash: str
    screen_hash: str


def _find(text: str, pattern: str, default: str = "unknown") -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else default


def parse_creepjs(text: str) -> CreepJSResult:
    """Extract key detection metrics from CreepJS text output."""

    fp_id = _find(text, r"FP ID:\s*([a-f0-9]+)")
    like_headless = _find(text, r"(\d+%)\s*like headless")
    headless = _find(text, r"(\d+%)\s*headless:")
    stealth = _find(text, r"(\d+%)\s*stealth")

    # GPU
    gpu_renderer = _find(text, r"(ANGLE [^\n]+)")
    gpu_vendor = _find(text, r"([A-Za-z][^\n]+)\nANGLE ")

    # User agent
    user_agent = _find(text, r"userAgent:\s*\n\s*(?:ua reduction\n\s*)?(Mozilla/[^\n]+)")
    if user_agent == "unknown":
        user_agent = _find(text, r"(Mozilla/5\.0[^\n]+)")

    # Platform
    platform = _find(text, r"device:\s*\n\s*(\w+)\s*\(")

    # Fonts
    fonts_loaded = _find(text, r"Fonts[a-f0-9]*\s*\n\s*load\s*\((\d+/\d+)\)")
    if fonts_loaded == "unknown":
        fonts_loaded = _find(text, r"load\s*\((\d+/\d+)\)")

    # Devices
    devices_count = _find(text, r"devices\s*\((\d+)\)")

    # Worker confidence
    worker_confidence = _find(text, r"confidence:\s*(high|moderate|low)")

    # Fingerprint hashes — section header hash is the 8-char hex after the section name
    # e.g. "Canvas 2d7ad7eeb5" → "7ad7eeb5", "Fontsb1d7a1b5" → "b1d7a1b5"
    # Also extract the data hash inside each section: "data: 3779b0f2"
    canvas_hash = _find(text, r"Canvas 2d([a-f0-9]+)")
    webgl_hash = _find(text, r"WebGL([a-f0-9]+)")
    audio_hash = _find(text, r"Audio([a-f0-9]+)")
    fonts_hash = _find(text, r"Fonts([a-f0-9]+)")
    domrect_hash = _find(text, r"DOMRect([a-f0-9]+)")
    svgrect_hash = _find(text, r"SVGRect([a-f0-9]+)")
    screen_hash = _find(text, r"Screen([a-f0-9]+)")

    return CreepJSResult(
        fp_id=fp_id,
        like_headless=like_headless,
        headless=headless,
        stealth=stealth,
        gpu_vendor=gpu_vendor,
        gpu_renderer=gpu_renderer,
        user_agent=user_agent,
        platform=platform,
        fonts_loaded=fonts_loaded,
        devices_count=devices_count,
        worker_confidence=worker_confidence,
        canvas_hash=canvas_hash,
        webgl_hash=webgl_hash,
        audio_hash=audio_hash,
        fonts_hash=fonts_hash,
        domrect_hash=domrect_hash,
        svgrect_hash=svgrect_hash,
        screen_hash=screen_hash,
    )
