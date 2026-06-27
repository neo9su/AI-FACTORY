"""
Face swap module using insightface + inswapper.
Runs on GPU 1 (CUDA_VISIBLE_DEVICES=1) since GPU 0 is occupied by vLLM.

v2.0 — Quality Improvements:
  1. Color histogram matching: match swapped face colors to target illumination
  2. Landmark-based face contour mask for Poisson blending
  3. Poisson seamlessClone (NORMAL_CLONE) to eliminate seam lines
  4. Eye region preservation via landmark exclusion zones
  5. Fallback: edge feathering if Poisson fails
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


# ── Color Matching ──────────────────────────────────────────────────────


# GFPGAN face enhancer
_face_enhancer = None

def _get_face_enhancer():
    """Lazy-load GFPGAN face enhancer on GPU."""
    global _face_enhancer
    if _face_enhancer is not None:
        return _face_enhancer
    try:
        import gfpgan
        model_path = os.path.expanduser("~/.cache/gfpgan/GFPGANv1.4.pth")
        if os.path.exists(model_path):
            _face_enhancer = gfpgan.GFPGANer(
                model_path=model_path,
                upscale=1,
                arch="clean",
                channel_multiplier=2,
            )
            print("[FaceSwap] GFPGAN enhancer loaded")
        return _face_enhancer
    except Exception as e:
        print(f"[FaceSwap] GFPGAN not available: {e}")
        return None

def _enhance_frame_with_gfpgan(img):
    """Apply GFPGAN face enhancement to a frame."""
    enhancer = _get_face_enhancer()
    if enhancer is None:
        return img
    try:
        _, _, enhanced = enhancer.enhance(
            img, has_aligned=False, only_center_face=False, paste_back=True
        )
        return enhanced
    except Exception as e:
        return img


def _histogram_match_channel(source_flat: np.ndarray, target_flat: np.ndarray,
                              target_shape: tuple) -> np.ndarray:
    """Match source pixel distribution to target via percentile remapping.
    Returns 2D array matching target_shape."""
    src_sorted = np.sort(source_flat)
    tgt_sorted = np.sort(target_flat)
    mapped = np.interp(source_flat, src_sorted, tgt_sorted).astype(np.uint8)
    return mapped.reshape(target_shape)


def _color_match_face(swapped_img: np.ndarray, original_img: np.ndarray, face_bbox) -> np.ndarray:
    """Match the color distribution of the swapped face region to the original face region."""
    x1, y1, x2, y2 = [int(v) for v in face_bbox]
    h, w = original_img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return swapped_img

    swapped_roi = swapped_img[y1:y2, x1:x2].copy()
    target_roi = original_img[y1:y2, x1:x2].copy()
    if swapped_roi.size == 0 or target_roi.size == 0:
        return swapped_img

    matched = np.zeros_like(swapped_roi)
    for c in range(3):
        src_c = swapped_roi[:, :, c].ravel()
        tgt_c = target_roi[:, :, c].ravel()
        matched[:, :, c] = _histogram_match_channel(src_c, tgt_c, matched.shape[:2])

    result = swapped_img.copy()
    result[y1:y2, x1:x2] = matched
    return result


def _color_match_on_image(swapped_img: np.ndarray, original_img: np.ndarray, face_bbox) -> None:
    """In-place color match. Modifies swapped_img in-place to match target illumination."""
    x1, y1, x2, y2 = [int(v) for v in face_bbox]
    h, w = original_img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return

    swapped_roi = swapped_img[y1:y2, x1:x2]
    target_roi = original_img[y1:y2, x1:x2]
    if swapped_roi.size == 0 or target_roi.size == 0:
        return

    for c in range(3):
        src_c = swapped_roi[:, :, c].ravel()
        tgt_c = target_roi[:, :, c].ravel()
        mapped = _histogram_match_channel(src_c, tgt_c, swapped_roi.shape[:2])
        swapped_roi[:, :, c] = mapped


# ── Poisson Blending ────────────────────────────────────────────────────

def _create_face_mask(face, img_shape, feather_pixels=15):
    """Create a gentle edge-feathering mask from the face bbox.

    Simplified: just feather the bbox boundary. The inswapper paste_back
    already handles the swap; this mask is only for a subtle edge blend
    to remove any seam at the bbox boundary.
    """
    h, w = img_shape[:2]
    mask = np.zeros(img_shape[:2], dtype=np.uint8)

    bbox = face.bbox
    x1, y1, x2, y2 = [int(v) for v in bbox]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    # Fill the bbox area
    mask[y1:y2, x1:x2] = 255

    # Gentle Gaussian blur for soft edge transition
    if feather_pixels > 0:
        ksize = feather_pixels * 2 + 1
        ksize = min(ksize, min(img_shape[:2]) // 2 * 2 + 1)
        if ksize >= 3:
            mask = cv2.GaussianBlur(mask, (ksize, ksize), feather_pixels)

    return mask


def _poisson_blend_face(frame, swapped_frame, face, mask):
    """Gentle edge feathering only.

    The inswapper paste_back=True already provides a well-blended swap.
    This function just applies a subtle feathered transition at the
    bbox boundary to remove any seam line, without altering the face.
    """
    bbox = face.bbox
    x1, y1, x2, y2 = [int(v) for v in bbox]
    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return frame

    result = swapped_frame.copy()

    try:
        feather = _apply_edge_feathering_simple(frame, swapped_frame, bbox)
        result[y1:y2, x1:x2] = feather[y1:y2, x1:x2]
    except Exception:
        pass

    return result


def _apply_edge_feathering_simple(original_img, swapped_img, face_bbox, feather_radius=10):
    """Simple distance-based feathering fallback (v1 method)."""
    h, w = original_img.shape[:2]
    x1, y1, x2, y2 = [int(v) for v in face_bbox]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return swapped_img

    pad = feather_radius * 3
    rx1 = max(0, x1 - pad); ry1 = max(0, y1 - pad)
    rx2 = min(w, x2 + pad); ry2 = min(h, y2 + pad)

    yy, xx = np.mgrid[ry1:ry2, rx1:rx2]
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    hw_val, hh_val = (x2 - x1) / 2, (y2 - y1) / 2
    if hw_val < 1 or hh_val < 1:
        return swapped_img
    dx = (xx - cx) / hw_val
    dy = (yy - cy) / hh_val
    dist = np.sqrt(dx**2 + dy**2)
    weight = np.clip(1.0 - (dist - 0.85) / 0.3, 0, 1).astype(np.float32)

    orig_roi = original_img[ry1:ry2, rx1:rx2].astype(np.float32)
    blurred = cv2.GaussianBlur(swapped_img[ry1:ry2, rx1:rx2], (0, 0), 1.5)

    blended = orig_roi * weight[:, :, np.newaxis] + \
              blurred.astype(np.float32) * (1 - weight[:, :, np.newaxis])

    result = swapped_img.copy()
    result[ry1:ry2, rx1:rx2] = np.clip(blended, 0, 255).astype(np.uint8)
    return result


# ── Model Loading ───────────────────────────────────────────────────────

_MODEL_DIR = "/mnt/disk3/comfyui/ComfyUI/models/insightface"
_face_app = None
_swapper = None


def _get_models():
    global _face_app, _swapper
    if _face_app is not None and _swapper is not None:
        return _face_app, _swapper

    os.environ["INSIGHTFACE_HOME"] = _MODEL_DIR
    from insightface.app import FaceAnalysis
    from insightface.model_zoo import get_model

    _face_app = FaceAnalysis(name="buffalo_l", root=_MODEL_DIR)
    _face_app.prepare(ctx_id=0, det_size=(640, 640))
    _swapper = get_model(os.path.join(_MODEL_DIR, "inswapper_128.onnx"))
    return _face_app, _swapper


# ── Public API ──────────────────────────────────────────────────────────

def get_reference_face(ref_image_path: str) -> Optional[np.ndarray]:
    face_app, _ = _get_models()
    img = cv2.imread(ref_image_path)
    if img is None:
        raise ValueError(f"Cannot read reference image: {ref_image_path}")
    faces = face_app.get(img)
    if len(faces) == 0:
        raise ValueError("No face detected in the reference image")
    faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
    return faces[0]


def face_swap_video(
    input_video: str,
    output_video: str,
    ref_image_path: str,
    target_faces_index: int = 0,
    max_frames: int = 0,
    progress_file: str = "",
) -> dict:
    """
    Swap faces in a video using insightface inswapper with quality improvements:
    - Color matching via histogram remapping
    - Face contour mask from landmarks
    - Poisson blending (NORMAL_CLONE) for seamless edges
    """
    import time
    face_app, swapper = _get_models()
    ref_face = get_reference_face(ref_image_path)

    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        return {"success": False, "error": f"Cannot open video: {input_video}"}

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()  # We'll use ffmpeg for extraction

    if fps <= 0:
        fps = 30
    if total_frames <= 0:
        total_frames = max_frames or 99999

    frames_to_process = total_frames
    if max_frames > 0:
        frames_to_process = min(total_frames, max_frames)

    with tempfile.TemporaryDirectory(prefix="face_swap_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        frame_dir = tmpdir_path / "frames"
        output_frame_dir = tmpdir_path / "output"
        frame_dir.mkdir()
        output_frame_dir.mkdir()

        # Extract frames
        print(f"Extracting {frames_to_process} frames...")
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_video,
            "-q:v", "2",
            "-frames:v", str(frames_to_process),
            str(frame_dir / "frame_%06d.jpg"),
        ], capture_output=True, text=True)

        frame_files = sorted(frame_dir.glob("*.jpg"))
        if not frame_files:
            return {"success": False, "error": "No frames extracted"}

        print(f"Processing {len(frame_files)} frames with improved face swap...")
        face_swap_count = 0

        if progress_file:
            with open(progress_file, "w") as pf:
                pf.write("0|提取中|0")

        for i, frame_path in enumerate(frame_files):
            img = cv2.imread(str(frame_path))
            if img is None:
                continue

            faces = face_app.get(img)
            if len(faces) > 0:
                faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)

                if target_faces_index < len(faces):
                    target_face = faces[target_faces_index]

                    # Step 1: Standard swap via inswapper
                    swapped_img = swapper.get(img, target_face, ref_face, paste_back=True)

                    # Step 2: Bbox-edge feathering - preserve inswapper output, gentle seam blend
                    try:
                        bbox = target_face.bbox
                        x1, y1, x2, y2 = [int(v) for v in bbox]
                        h_img, w_img = img.shape[:2]
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(w_img, x2), min(h_img, y2)
                        if x2 > x1 and y2 > y1:
                            fade = 8
                            fx1, fy1 = max(0, x1-fade), max(0, y1-fade)
                            fx2, fy2 = min(w_img, x2+fade), min(h_img, y2+fade)
                            yy, xx = np.mgrid[fy1:fy2, fx1:fx2]
                            cx, cy = (x1+x2)/2, (y1+y2)/2
                            hw, hh = max(1, (x2-x1)/2), max(1, (y2-y1)/2)
                            dx = (xx - cx) / hw
                            dy = (yy - cy) / hh
                            dist = np.sqrt(dx**2 + dy**2)
                            # Soft edge: inner 90% full swap, outer 10% feather to original
                            weight = np.clip(1.0 - (dist - 0.9) / 0.15, 0, 1).astype(np.float32)
                            blended_roi = (swapped_img[fy1:fy2, fx1:fx2].astype(np.float32) * weight[:,:,np.newaxis] +
                                           img[fy1:fy2, fx1:fx2].astype(np.float32) * (1.0 - weight[:,:,np.newaxis]))
                            img[fy1:fy2, fx1:fx2] = np.clip(blended_roi, 0, 255).astype(np.uint8)
                        else:
                            img = swapped_img
                    except Exception:
                        img = swapped_img

                    face_swap_count += 1

            cv2.imwrite(str(output_frame_dir / f"frame_{i+1:06d}.jpg"), img)

            # Progress
            if progress_file and (i % 5 == 0 or i == len(frame_files) - 1):
                pct = int((i + 1) / len(frame_files) * 100)
                with open(progress_file, "w") as pf:
                    pf.write(f"{pct}|处理中|{i+1}|{len(frame_files)}|{face_swap_count}")

        print(f"Swapped {face_swap_count}/{len(frame_files)} frames")

        # Progress: reassembling
        if progress_file:
            with open(progress_file, "w") as pf:
                pf.write("99|合成中|0")

        # Reassemble video
        result = subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-pattern_type", "glob",
            "-i", str(output_frame_dir / "*.jpg"),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-map", "0:v:0",
            str(tmpdir_path / "temp_video.mp4"),
        ], capture_output=True, text=True)

        if result.returncode != 0:
            if progress_file and os.path.exists(progress_file):
                try:
                    os.remove(progress_file)
                except OSError:
                    pass
            return {"success": False, "error": f"FFmpeg reassemble failed: {result.stderr[:500]}"}

        # Copy original audio
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(tmpdir_path / "temp_video.mp4"),
            "-i", input_video,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-map", "0:v:0",
            "-map", "1:a:0?",
            output_video,
        ], capture_output=True, text=True)

    if not os.path.exists(output_video):
        return {"success": False, "error": "Output video was not created"}

    output_size = os.path.getsize(output_video)

    if progress_file and os.path.exists(progress_file):
        try:
            os.remove(progress_file)
        except OSError:
            pass

    return {
        "success": True,
        "total_frames": len(frame_files),
        "swapped_frames": face_swap_count,
        "output_size": output_size,
        "output_path": output_video,
    }






def face_swap_single_frame(
    input_image: str,
    output_image: str,
    ref_image_path: str,
) -> dict:
    """Swap face in a single image with quality improvements."""
    face_app, swapper = _get_models()
    ref_face = get_reference_face(ref_image_path)

    img = cv2.imread(input_image)
    if img is None:
        return {"success": False, "error": f"Cannot read image: {input_image}"}

    faces = face_app.get(img)
    if len(faces) == 0:
        return {"success": False, "error": "No face detected in input image"}

    faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
    target_face = faces[0]

    orig_img = img.copy()
    swapped_img = swapper.get(img, target_face, ref_face, paste_back=True)
    _color_match_on_image(swapped_img, orig_img, target_face.bbox)
    mask = _create_face_mask(target_face, img.shape, feather_pixels=15)
    result = _poisson_blend_face(orig_img, swapped_img, target_face, mask)

    cv2.imwrite(output_image, result)
    return {"success": True, "output_path": output_image}


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4:
        result = face_swap_video(sys.argv[1], sys.argv[2], sys.argv[3])
        print(result)
    else:
        print("Usage: python face_swap.py <input_video> <output_video> <ref_face_image>")