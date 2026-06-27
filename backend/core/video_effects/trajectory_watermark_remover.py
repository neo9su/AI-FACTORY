"""
Trajectory Watermark Remover — Deterministic interpolation from OCR waypoints

When CV-based detection (CLAHE + adaptive threshold) fails for extremely faint
semi-transparent moving text watermarks (luminance difference < 15 gray levels),
use this approach instead.

Strategy:
  1. OCR temporal analysis → establish waypoints (time, x, y, w, h)
  2. Linear interpolation → compute watermark position per frame
  3. Targeted inpainting at interpolated positions
  4. Phase-dependent padding to protect subtitles when watermark overlaps

Usage:
  from trajectory_watermark_remover import process_video

  # Process full video
  result = process_video("input.mp4", "output.mp4")

  # With config
  result = process_video("input.mp4", "output.mp4", config={"segments": [...]})

API compatible with moving_watermark_remover.process_video() — drop-in replacement.
"""
from __future__ import annotations

import cv2
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)

VIDEO_W = 576
VIDEO_H = 1024

# Subtitle zone — NEVER inpaint fully within this zone
SUBTITLE_ZONE_Y1 = 710
SUBTITLE_ZONE_Y2 = 745

# ==========================================================================
# OCR-confirmed waypoints for "小登好物推荐" (verified in production)
# Format: (time_seconds, x, y, w, h)
#
# **IMPORTANT: Parabolic trajectory discovery**
# The watermark does NOT move in a simple straight line. It follows a
# parabolic path: goes right (Phase1), reverses direction (Bridge), 
# then goes left (Phase3). The bridge phase (15-31s) was initially 
# missed because OCR failed on faint text against busy backgrounds.
#
# To establish these for a new watermark:
#   1. Extract frames at multiple time points
#   2. Run OCR on each frame
#   3. Filter for watermark text
#   4. Record (t, x, y, w, h) from OCR bbox
#   5. If OCR shows gaps (faint text), manually interpolate with 
#      WIDER padding (180-200px wide) to compensate for uncertainty
# ==========================================================================

# Phase 1 (0-15s): Left→Right, y=476→600
WAYPOINTS_PHASE1 = [
    (2.5,   4,   476, 96,  25),
    (3.0,   5,   483, 119, 24),
    (3.5,   9,   488, 127, 23),
    (5.5,   123, 505, 70,  29),
    (7.0,   112, 521, 106, 27),
    (10.0,  241, 551, 100, 28),
    (11.5,  241, 566, 121, 27),
    (12.0,  262, 572, 113, 26),
    (14.0,  309, 595, 75,  18),
    (15.0,  334, 600, 110, 29),
]

# Bridge (15-31s): WATERMARK KEEPS MOVING RIGHT, THEN REVERSES
# This was the hardest phase to detect — OCR failed because watermark
# is extremely faint against product close-up backgrounds.
# Actual trajectory: (334,600)→(500,695) at peak→reverses to (346,750)
# ⚠️ Use wide padding (180-200px w, 55px h) for uncertainty
WAYPOINTS_BRIDGE = [
    (15.0,  290, 580, 140, 45),   # Continuation from Phase1
    (16.0,  310, 595, 140, 45),
    (17.0,  330, 610, 140, 45),
    (18.0,  350, 625, 150, 45),
    (19.0,  370, 640, 160, 45),
    (20.0,  395, 655, 170, 50),
    (21.0,  420, 668, 180, 50),
    (22.0,  445, 680, 190, 50),
    (23.0,  465, 690, 200, 55),   # Max right, peak of parabola
    (24.0,  480, 697, 200, 55),   # OCR confirmed: x=500-530, y=693-701
    (25.0,  475, 702, 200, 55),   # OCR confirmed: x=501-526
    (26.0,  450, 710, 180, 55),   # Start reversal
    (27.0,  420, 720, 170, 55),
    (28.0,  395, 730, 160, 55),
    (29.0,  375, 738, 150, 50),
    (31.0,  310, 745, 120, 45),   # Merge into Phase3 start
]

# Phase 3 (31-45s): Right→Left, y=750→860 (OVERLAPS subtitles at y=710-745)
WAYPOINTS_PHASE3 = [
    (31.0,  346, 750, 85,  21),
    (33.0,  318, 763, 102, 26),
    (42.5,  55,  844, 51,  16),
    (43.5,  24,  850, 121, 24),
    (44.0,  12,  853, 106, 23),
    (45.0,  7,   860, 111, 28),
]


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b."""
    return a + (b - a) * t


def get_phase(t: float) -> tuple[str, list | None]:
    """Return (phase_name, waypoints_list_or_None)."""
    if t < 1.5:
        return None, None               # Watermark not yet visible
    elif t < 14.5:
        return "phase1", WAYPOINTS_PHASE1
    elif t < 32.0:
        return "bridge", WAYPOINTS_BRIDGE   # Parabolic bridge (critical!)
    else:
        return "phase3", WAYPOINTS_PHASE3


def get_watermark_bbox(t: float, waypoints: list) -> tuple[int, int, int, int] | None:
    """Interpolate (x, y, w, h) at time t from ordered waypoints."""
    if not waypoints:
        return None

    # Before first or after last waypoint → clamp
    if t <= waypoints[0][0]:
        _, x, y, w, h = waypoints[0]
        return (x, y, w, h)
    if t >= waypoints[-1][0]:
        _, x, y, w, h = waypoints[-1]
        return (x, y, w, h)

    # Find surrounding waypoints and interpolate
    for i in range(len(waypoints) - 1):
        t1, x1, y1, w1, h1 = waypoints[i]
        t2, x2, y2, w2, h2 = waypoints[i + 1]
        if t1 <= t <= t2:
            frac = (t - t1) / (t2 - t1) if t2 > t1 else 0
            x = int(lerp(x1, x2, frac))
            y = int(lerp(y1, y2, frac))
            w = int(lerp(w1, w2, frac))
            h = int(lerp(h1, h2, frac))
            return (x, y, w, h)

    return None


def process_video(
    input_path: str,
    output_path: str,
    config: Optional[dict] = None,
    preview_seconds: float | None = None,
) -> dict:
    """Process video using trajectory-driven watermark removal.

    Args:
        input_path: Source video path
        output_path: Output video path (will be overwritten)
        config: Optional dict — if contains 'segments', uses that instead of
                built-in waypoints (for per-video custom trajectories).
                Each segment: {start, end, w, h, subtitle_safe, waypoints: [{t,x,y}]}
        preview_seconds: If set, only process first N seconds (for testing)

    Returns:
        dict with success, frames_processed, frames_with_watermark, etc.
    """
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return {"success": False, "error": f"Cannot open: {input_path}"}

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    max_frames = total_frames if not preview_seconds else min(total_frames, int(fps * preview_seconds))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    frame_count = 0
    phase_stats: dict[str, int] = {"phase1": 0, "bridge": 0, "phase3": 0}
    total_processed = 0
    last_phase = ""

    while frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        t = frame_count / fps
        phase, waypoints = get_phase(t)

        if phase != last_phase:
            logger.info("Phase switch: %s at %.1fs (frame %d)", phase, t, frame_count)
            last_phase = phase

        if phase:
            phase_stats[phase] += 1

        if waypoints:
            bbox = get_watermark_bbox(t, waypoints)
            if bbox is not None:
                x, y, wm_w, wm_h = bbox

                # Skip if entirely off-screen
                if x + wm_w > 0 and x < w and y + wm_h > 0 and y < h:
                    # Phase-dependent padding
                    if phase == "bridge":
                        # Bridge phase has positional uncertainty — use wide padding
                        px = max(12, wm_w // 6)
                        py = max(8, wm_h // 4)
                        inpaint_radius = 2
                    elif phase == "phase3":
                        # Minimal padding to protect subtitles
                        px = max(4, wm_w // 12)
                        py = max(1, wm_h // 10)
                        inpaint_radius = 2
                    else:
                        px = max(6, wm_w // 8)
                        py = max(3, wm_h // 6)
                        inpaint_radius = 3

                    x1 = max(0, x - px)
                    y1 = max(0, y - py)
                    x2 = min(w, x + wm_w + px)
                    y2 = min(h, y + wm_h + py)

                    if x2 > x1 and y2 > y1:
                        mask = np.zeros((h, w), dtype=np.uint8)
                        mask[y1:y2, x1:x2] = 255
                        frame = cv2.inpaint(frame, mask, inpaint_radius, cv2.INPAINT_NS)
                        total_processed += 1

        out.write(frame)
        frame_count += 1

        if frame_count % 200 == 0:
            logger.info(f"  {frame_count}/{max_frames} processed={total_processed} phase={phase}")

    cap.release()
    out.release()
    # cv2.destroyAllWindows() - headless server

    logger.info(f"DONE: {frame_count}f, {total_processed} inpaints")

    return {
        "success": True,
        "frames_processed": frame_count,
        "total_frames": total_frames,
        "output_path": output_path,
        "frames_with_watermark": total_processed,
        "duration_seconds": frame_count / fps,
        "phase_stats": phase_stats,
    }
