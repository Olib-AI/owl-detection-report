"""Owl Browser REST API client."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

import os

WAIT_TIME_MS = 15_000
REQUEST_TIMEOUT = 90


@dataclass(slots=True)
class OwlResult:
    screenshot_png: bytes
    text: str


class OwlClient:
    """Thin wrapper around the Owl Browser REST API."""

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        # /api prefix for nginx proxy, empty for direct connection to port 8080
        self._api_prefix = os.environ.get("OWL_API_PREFIX", "/api")
        self._session = requests.Session()
        self._session.headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )

    def _execute(self, tool_name: str, payload: dict[str, object] | None = None) -> object:
        url = f"{self._base_url}{self._api_prefix}/execute/{tool_name}"
        logger.debug("POST %s %s", url, payload)
        resp = self._session.post(url, json=payload or {}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and not data.get("success"):
            raise RuntimeError(f"{tool_name} failed: {data}")
        return data.get("result", data) if isinstance(data, dict) else data

    def get_version(self) -> str:
        """Fetch Owl Browser version from the health endpoint."""
        try:
            resp = self._session.get(f"{self._base_url}/health", timeout=10)
            resp.raise_for_status()
            return resp.json().get("version", "unknown")
        except Exception:
            logger.warning("Could not fetch Owl Browser version", exc_info=True)
            return "unknown"

    def run_creepjs(self, profile_os: str) -> OwlResult:
        """Create a context, navigate to CreepJS, capture results, and close."""
        context_id: str | None = None
        try:
            # 1. Create context with OS profile
            resp = self._execute(
                "browser_create_context", {"os": profile_os, "screen_size": "1920x1080"}
            )
            context_id = str(resp["context_id"])
            logger.info("Created Owl context %s for profile_os=%s", context_id, profile_os)

            # 2. Navigate
            self._execute(
                "browser_navigate",
                {
                    "context_id": context_id,
                    "url": "https://abrahamjuliot.github.io/creepjs/",
                    "wait_until": "networkidle",
                },
            )
            logger.info("Navigated to CreepJS")

            # 3. Wait for fingerprint computation
            self._execute(
                "browser_wait",
                {"context_id": context_id, "timeout": WAIT_TIME_MS},
            )
            logger.info("Waited %dms for CreepJS to compute", WAIT_TIME_MS)

            # 4. Screenshot
            shot_resp = self._execute(
                "browser_screenshot",
                {"context_id": context_id, "mode": "fullpage"},
            )
            screenshot_png = base64.b64decode(str(shot_resp))

            # 5. Get text for parsing
            text = str(self._execute(
                "browser_extract_text", {"context_id": context_id}
            ))

            return OwlResult(screenshot_png=screenshot_png, text=text)
        finally:
            if context_id is not None:
                try:
                    self._execute(
                        "browser_close_context", {"context_id": context_id}
                    )
                    logger.info("Closed Owl context %s", context_id)
                except Exception:
                    logger.warning("Failed to close Owl context %s", context_id, exc_info=True)
