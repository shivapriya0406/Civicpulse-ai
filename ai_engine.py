"""Lightweight, explainable keyword and image-property triage."""

from __future__ import annotations

from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

CATEGORIES = (
    "Roads & Infrastructure",
    "Water & Drainage",
    "Garbage & Sanitation",
    "Streetlights & Electricity",
    "General Civic Issue",
)

KEYWORDS = {
    "Roads & Infrastructure": (
        "pothole", "road", "pavement", "sidewalk", "footpath", "bridge",
        "crack", "traffic sign", "street surface",
    ),
    "Water & Drainage": (
        "water", "leak", "pipe", "drain", "flood", "sewage", "sewer",
        "waterlogging", "blocked drain",
    ),
    "Garbage & Sanitation": (
        "garbage", "trash", "waste", "litter", "dump", "rubbish", "bin",
        "sanitation", "unclean",
    ),
    "Streetlights & Electricity": (
        "streetlight", "street light", "lamp", "electric", "power", "wire",
        "outage", "pole", "dark street",
    ),
}

CRITICAL_TERMS = (
    "exposed wire", "live wire", "electrocution", "collapsed", "collapse",
    "sinkhole", "burst pipe", "major flooding", "fire", "dangerous",
    "life threatening", "urgent",
)
MEDIUM_TERMS = (
    "large", "deep", "overflow", "blocked", "broken", "severe", "multiple",
    "unsafe", "not working", "leaking",
)


def _similarity(left: str, right: str) -> float:
    """Compare normalized text, ignoring case and repeated whitespace."""
    normalized_left = " ".join((left or "").casefold().split())
    normalized_right = " ".join((right or "").casefold().split())
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def is_duplicate_issue(
    new_loc: str,
    new_desc: str,
    existing_loc: str,
    existing_desc: str,
    same_category: bool = False,
) -> bool:
    """Match reports by similar location and description, or category+location."""
    location_similarity = _similarity(new_loc, existing_loc)
    description_similarity = _similarity(new_desc, existing_desc)
    return (location_similarity > 0.6 and description_similarity > 0.5) or (
        same_category and location_similarity > 0.8
    )


def verify_proof_of_work(
    before_image_path: str | Path, after_image_path: str | Path
) -> tuple[bool, float, str]:
    """Normalize camera lighting, then compare road and roadside structure."""
    try:
        with Image.open(before_image_path) as before_source:
            before = ImageOps.equalize(
                ImageOps.exif_transpose(before_source).convert("L")
            ).resize(
                (256, 256), Image.Resampling.LANCZOS
            )
        with Image.open(after_image_path) as after_source:
            after = ImageOps.equalize(
                ImageOps.exif_transpose(after_source).convert("L")
            ).resize(
                (256, 256), Image.Resampling.LANCZOS
            )
        before_pixels = np.asarray(before, dtype=np.float32)
        after_pixels = np.asarray(after, dtype=np.float32)
        pixel_difference = np.abs(before_pixels - after_pixels) / 255.0 * 100.0

        edge_width = int(256 * 0.20)
        center_start = edge_width
        center_end = 256 - edge_width
        structural_zones = np.concatenate(
            (
                pixel_difference[64:220, :edge_width].ravel(),
                pixel_difference[64:220, center_end:].ravel(),
            )
        )
        road_zone = pixel_difference[80:240, center_start:center_end]
        structural_border_diff = float(np.mean(structural_zones))
        road_surface_diff = float(np.mean(road_zone))
    except (OSError, ValueError, UnidentifiedImageError):
        return (
            False,
            0.0,
            "Verification Failed: Unable to read both images. Please upload valid photos.",
        )

    if road_surface_diff < 10.0 and structural_border_diff < 10.0:
        return (
            False,
            round(100 - road_surface_diff, 1),
            "Verification Failed: After photo is identical to Before photo. No repair detected.",
        )
    if structural_border_diff > 48.0:
        return (
            False,
            round(structural_border_diff, 1),
            "Verification Failed: Roadside surroundings do not match the original location.",
        )
    return (
        True,
        round(road_surface_diff, 1),
        "Verified Resolved: Roadside landmarks match (camera & lighting normalized) and road repair is confirmed!",
    )


def _image_signals(image_path: str | Path | None) -> tuple[bool, bool]:
    """Return (image_present, unusually_large_or_detailed) safely."""
    if not image_path:
        return False, False
    try:
        with Image.open(image_path) as image:
            width, height = image.size
            return True, width * height >= 2_000_000 or min(width, height) >= 1600
    except (OSError, UnidentifiedImageError, ValueError):
        return False, False


def analyze_complaint_ai(description: str, image_path: str | None) -> tuple[str, str]:
    """Classify a civic issue and estimate severity using basic heuristics."""
    text = (description or "").casefold()
    scores = {
        category: sum(1 for keyword in words if keyword in text)
        for category, words in KEYWORDS.items()
    }
    best_category = max(scores, key=scores.get) if scores else None
    category = (
        best_category
        if best_category and scores[best_category] > 0
        else "General Civic Issue"
    )

    image_present, detailed_image = _image_signals(image_path)
    if any(term in text for term in CRITICAL_TERMS):
        severity = "Critical"
    elif sum(1 for term in MEDIUM_TERMS if term in text) >= 2 or (
        detailed_image and any(term in text for term in MEDIUM_TERMS)
    ):
        severity = "Medium"
    elif any(term in text for term in MEDIUM_TERMS) or (image_present and detailed_image):
        severity = "Medium"
    else:
        severity = "Low"
    return category, severity
