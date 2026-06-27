"""
Watermark Removal Module — OpenCV-based inpainting approach

Detects and removes common video watermarks/overlays using:
1. Region-based inpainting (Telea's method)
2. Configurable target zones
"""

from __future__ import annotations

import cv2
import numpy as np
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Common watermark zones as fractions of (width, height)
# Format: (x_start_frac, y_start_frac, x_end_frac, y_end_frac, name)
COMMON_WATERMARK_ZONES = [
    (0.85, 0.82, 1.0, 0.98, "bottom_right_logo"),      # 右下角平台水印
    (0.0, 0.92, 1.0, 1.0, "bottom_bar"),                 # 底部栏（点赞/评论/分享）
    (0.85, 0.0, 1.0, 0.12, "top_right_handle"),          # 右上角账号
    (0.0, 0.0, 0.2, 0.08, "top_left_handle"),            # 左上角账号
    (0.3, 0.85, 0.7, 0.95, "bottom_center_text"),        # 底部中间文字
]


def detect_watermark_regions(
    frame: np.ndarray,
    sensitivity: float = 1.0,
) -> list[tuple[int, int, int, int, float]]:
    """Auto-detect watermark regions using edge + color analysis.

    Returns list of (x, y, w, h, confidence) for each suspected region.
    """
    h, w = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    regions = []

    # Strategy 1: Look for semi-transparent overlays in corners
    # Watermarks often have low edge density but persistent color
    for x1_f, y1_f, x2_f, y2_f, name in COMMON_WATERMARK_ZONES:
        x1, y1 = int(x1_f * w), int(y1_f * h)
        x2, y2 = int(x2_f * w), int(y2_f * h)
        region = gray[y1:y2, x1:x2]
        if region.size == 0:
            continue

        avg_bright = np.mean(region)
        std_bright = np.std(region)
        edges = cv2.Canny(region, 30, 100)
        edge_density = np.sum(edges > 0) / region.size

        # Color analysis
        color_region = frame[y1:y2, x1:x2]
        b_mean = np.mean(color_region[:, :, 0])
        g_mean = np.mean(color_region[:, :, 1])
        r_mean = np.mean(color_region[:, :, 2])

        # Confidence scoring
        confidence = 0.0
        # High std in brightness suggests text/logo
        if std_bright > 20:
            confidence += 0.2
        if std_bright > 40:
            confidence += 0.2
        # Low-moderate edge density (text has edges but not too many)
        if 0.01 < edge_density < 0.15:
            confidence += 0.2
        # Color bias (logos often have distinct colors)
        color_range = max(r_mean, g_mean, b_mean) - min(r_mean, g_mean, b_mean)
        if color_range > 20:
            confidence += 0.2
        # Semi-transparent overlay often has unusual brightness
        if avg_bright > 200 or avg_bright < 60:
            if std_bright > 15:
                confidence += 0.2

        confidence *= sensitivity

        if confidence > 0.3:
            regions.append((x1, y1, x2 - x1, y2 - y1, confidence))
            logger.debug(
                "Detected zone %s: confidence=%.2f bright=%.0f std=%.0f edge=%.2f",
                name, confidence, avg_bright, std_bright, edge_density,
            )

    return regions


def remove_watermark_inpaint(
    frame: np.ndarray,
    roi: tuple[int, int, int, int],
    method: str = "telea",
    inpaint_radius: int = 5,
) -> np.ndarray:
    """Remove watermark from a specific region using inpainting.

    Args:
        frame: Input BGR frame
        roi: (x, y, w, h) region of interest
        method: 'telea' or 'ns' (Navier-Stokes)
        inpaint_radius: Radius for inpainting

    Returns:
        Frame with watermark removed in the ROI
    """
    result = frame.copy()
    x, y, w, h = roi
    if w <= 0 or h <= 0:
        return result

    # Create mask for the ROI
    mask = np.zeros(frame.shape[:2], dtype=np.uint8)
    mask[y:y+h, x:x+w] = 255

    # Apply inpainting
    method_flag = cv2.INPAINT_TELEA if method == "telea" else cv2.INPAINT_NS
    result = cv2.inpaint(result, mask, inpaint_radius, method_flag)

    return result


def remove_watermarks_multi(
    frame: np.ndarray,
    zones: Optional[list[tuple[float, float, float, float]]] = None,
    auto_detect: bool = True,
    sensitivity: float = 1.0,
    inpaint_radius: int = 5,
) -> np.ndarray:
    """Remove watermarks from a frame using multiple detection methods.

    Args:
        frame: Input BGR frame
        zones: Optional list of (x1_frac, y1_frac, x2_frac, y2_frac) zones
        auto_detect: Whether to auto-detect watermark regions
        sensitivity: Detection sensitivity (0.0-2.0)
        inpaint_radius: Inpainting radius

    Returns:
        Clean frame
    """
    result = frame.copy()
    h, w = frame.shape[:2]

    # Apply user-specified zones
    if zones:
        for x1_f, y1_f, x2_f, y2_f in zones:
            x1 = int(x1_f * w)
            y1 = int(y1_f * h)
            x2 = int(x2_f * w)
            y2 = int(y2_f * h)
            roi = (x1, y1, x2 - x1, y2 - y1)
            result = remove_watermark_inpaint(result, roi, inpaint_radius=inpaint_radius)

    # Auto-detect additional regions
    if auto_detect:
        regions = detect_watermark_regions(frame, sensitivity=sensitivity)
        for x, y, rw, rh, conf in regions:
            # Skip if this region overlaps with user-specified zones
            if zones:
                overlaps = False
                for zx1_f, zy1_f, zx2_f, zy2_f in zones:
                    zx1 = int(zx1_f * w)
                    zy1 = int(zy1_f * h)
                    zx2 = int(zx2_f * w)
                    zy2 = int(zy2_f * h)
                    if (x < zx2 and x + rw > zx1 and y < zy2 and y + rh > zy1):
                        overlaps = True
                        break
                if overlaps:
                    continue
            roi = (x, y, rw, rh)
            result = remove_watermark_inpaint(result, roi, inpaint_radius=inpaint_radius)
            logger.info("Auto-removed watermark at (%d,%d %dx%d) conf=%.2f", x, y, rw, rh, conf)

    return result


def process_video(
    input_path: str,
    output_path: str,
    zones: Optional[list[tuple[float, float, float, float]]] = None,
    auto_detect: bool = True,
    sensitivity: float = 1.0,
    inpaint_radius: int = 5,
    preview_seconds: Optional[float] = None,
) -> dict:
    """Process a video file to remove watermarks.

    Args:
        input_path: Input video path
        output_path: Output video path
        zones: Manual zone definitions as (x1_frac, y1_frac, x2_frac, y2_frac)
        auto_detect: Whether to auto-detect watermarks
        sensitivity: Detection sensitivity
        inpaint_radius: Inpainting radius
        preview_seconds: If set, only process first N seconds for testing

    Returns:
        dict with success, frames_processed, output_path
    """
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return {"success": False, "error": f"Cannot open video: {input_path}"}

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Calculate max frames to process
    max_frames = total_frames
    if preview_seconds:
        max_frames = min(total_frames, int(fps * preview_seconds))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    frame_count = 0
    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        cleaned = remove_watermarks_multi(
            frame,
            zones=zones,
            auto_detect=auto_detect,
            sensitivity=sensitivity,
            inpaint_radius=inpaint_radius,
        )
        out.write(cleaned)
        frame_count += 1

        if frame_count % 30 == 0:
            logger.info("Processed %d/%d frames", frame_count, max_frames)

    cap.release()
    out.release()
    # cv2.destroyAllWindows() - headless server

    return {
        "success": True,
        "frames_processed": frame_count,
        "total_frames": total_frames,
        "output_path": output_path,
        "duration_seconds": frame_count / fps,
    }
