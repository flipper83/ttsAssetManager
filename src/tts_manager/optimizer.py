"""Image resizing/compression applied to assets before upload."""

from pathlib import Path

from PIL import Image

from .progress import EventKind, ProgressCallback, ProgressEvent, noop

MAX_IMAGE_DIMENSION = 2048
MAX_SHEET_DIMENSION = 4096

_SAVE_FORMATS = {"PNG", "JPEG", "WEBP"}


def resize_to_fit(img: Image.Image, max_dimension: int) -> Image.Image:
    """Return img downscaled proportionally if its longest side exceeds max_dimension."""
    if max(img.size) <= max_dimension:
        return img
    ratio = max_dimension / max(img.size)
    new_size = (max(1, round(img.width * ratio)), max(1, round(img.height * ratio)))
    return img.resize(new_size, Image.LANCZOS)


def optimize_image(
    src: Path,
    dest: Path,
    max_dimension: int = MAX_IMAGE_DIMENSION,
    on_progress: ProgressCallback = noop,
) -> Path:
    """Resize (if oversized) and re-save src at dest, keeping its original format.

    Uses lossless re-encoding (optimize=True) — no quality is sacrificed beyond
    the resize itself.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)

    img = Image.open(src)
    img.load()
    fmt = img.format if img.format in _SAVE_FORMATS else "PNG"
    img = resize_to_fit(img, max_dimension)
    if fmt == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(dest, fmt, optimize=True)
    img.close()

    before = src.stat().st_size
    after = dest.stat().st_size
    if after < before:
        saved_pct = round((1 - after / before) * 100)
        on_progress(ProgressEvent(
            EventKind.INFO,
            f"Optimized {src.name}: {before // 1024}KB → {after // 1024}KB (-{saved_pct}%)",
        ))
    return dest
