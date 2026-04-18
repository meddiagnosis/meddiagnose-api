"""
Extract image bytes from uploaded files for AI vision analysis.

Supports: jpg, png, webp, gif (direct), PDF (extract embedded images),
DICOM (convert to PNG). Video frames are not extracted.
"""

import base64
import io
import logging
from pathlib import Path

logger = logging.getLogger("image_extraction")

# MIME types for direct image formats
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
IMAGE_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def extract_images_from_file(content: bytes, filename: str) -> list[tuple[bytes, str]]:
    """
    Extract image bytes and MIME types from an uploaded file.

    Returns list of (image_bytes, mime_type) for direct images or extracted images.
    Empty list if no images could be extracted.
    """
    ext = Path(filename or "").suffix.lower()
    results: list[tuple[bytes, str]] = []

    if ext in IMAGE_EXTENSIONS:
        mime = IMAGE_MIME.get(ext, "image/jpeg")
        results.append((content, mime))
        return results

    if ext == ".pdf":
        return _extract_from_pdf(content)

    if ext in (".dcm", ".dicom"):
        img = _dicom_to_image(content)
        if img:
            results.append((img, "image/png"))
        return results

    # Video, unknown: skip
    return results


def _extract_from_pdf(content: bytes) -> list[tuple[bytes, str]]:
    """Extract embedded images from PDF using pypdf."""
    results: list[tuple[bytes, str]] = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        for page in reader.pages:
            images_attr = getattr(page, "images", None)
            if images_attr is None:
                continue
            for name in getattr(images_attr, "keys", lambda: [])():
                try:
                    img_obj = images_attr[name]
                    if hasattr(img_obj, "image") and img_obj.image:
                        buf = io.BytesIO()
                        img_obj.image.save(buf, format="PNG")
                        results.append((buf.getvalue(), "image/png"))
                except Exception as e:
                    logger.debug("PDF image extract skip %s: %s", name, e)
    except Exception as e:
        logger.warning("PDF extraction failed: %s", e)
    return results


def _dicom_to_image(content: bytes) -> bytes | None:
    """Convert DICOM to PNG bytes using pydicom and Pillow."""
    try:
        import pydicom
        from PIL import Image
        import numpy as np

        dcm = pydicom.dcmread(io.BytesIO(content))
        arr = dcm.pixel_array
        # Normalize to 0-255
        if arr.max() > arr.min():
            arr = ((arr - arr.min()) / (arr.max() - arr.min()) * 255).astype(np.uint8)
        else:
            arr = np.zeros_like(arr, dtype=np.uint8)
        if len(arr.shape) == 3:
            img = Image.fromarray(arr)
        else:
            img = Image.fromarray(arr).convert("L")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        logger.warning("DICOM conversion failed: %s", e)
        return None


def images_to_base64_data_urls(images: list[tuple[bytes, str]]) -> list[str]:
    """
    Convert (bytes, mime) pairs to Ollama-compatible data URLs.

    Ollama expects: ["data:image/png;base64,...", ...]
    """
    out: list[str] = []
    for raw, mime in images:
        b64 = base64.b64encode(raw).decode("utf-8")
        out.append(f"data:{mime};base64,{b64}")
    return out
