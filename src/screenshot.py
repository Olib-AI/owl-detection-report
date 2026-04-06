"""PNG to WebP conversion."""

from __future__ import annotations

import io
import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


def save_webp(png_data: bytes, dest: Path, quality: int = 80) -> None:
    """Convert PNG bytes to WebP and save."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(io.BytesIO(png_data))
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=quality, method=4)
    dest.write_bytes(buf.getvalue())
    logger.info("Saved %s (PNG %dKB -> WebP %dKB)", dest.name, len(png_data) // 1024, len(buf.getvalue()) // 1024)
