"""
Smart face swap: embedding-based identity matching across multiple persons.
Uses video-frame reference embeddings (cosine similarity) to identify
which detected face matches which identity, then applies the correct
AI-generated source face.

Completely bypasses FaceFusion's face selection + age/gender classifier
(inaccurate for Asian faces).

Pipeline-compatible: same return signature as face_swap_video().
"""
import cv2
import numpy as np
import os
import json
import time
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model
from scipy.spatial.distance import cosine

logger = logging.getLogger(__name__)

# ── Global model cache (shared across calls) ────────────────────────────

_face_app: Optional[FaceAnalysis] = None
_swapper: Optional[any] = None


def _get_models():
    """Lazy-load insightface app + inswapper (GPU)."""
    global _face_app, _swapper
    if _face_app is None:
        _face_app = FaceAnalysis(
            name='buffalo_l',
            root='/home/neo/.insightface/models',
            providers=['CUDAExecutionProvider'],
        )
        _face_app.prepare(ctx_id=0, det_size=(640, 640))
    if _swapper is None:
        model_root = '/mnt/disk3/facefusion/.assets/models'
        swapper_path = os.path.join(model_root, 'inswapper_128_fp16.onnx')
        if not os.path.exists(swapper_path):
            swapper_path = os.path.join(model_root, 'inswapper_128.onnx')
        _swapper = get_model(swapper_path)
    return _face_app, _swapper


def _load_face(path: str):
    """Load an image, detect the first face, return (img, face_obj)."""
    img = cv2.imread(path)
    if img is None:
        return None, None
    app, _ = _get_models()
    faces = app.get(img)
    if not faces:
        return None, None
    return img, faces[0]


def _load_ref_embedding(path: str):
    """Load a video-reference frame and return its first face's normed embedding."""
    app, _ = _get_models()
    img = cv2.imread(path)
    if img is None:
        return None
    faces = app.get(img)
    if not faces:
        return None
    return faces[0].normed_embedding


# ── Convert smart_swap standalone script logic into pipeline function ───

def smart_swap_video(
    input_video: str,
    output_video: str,
    swap_config: dict,
    max_frames: int = 0,
    progress_file: str = "",
) -> dict:
    """
    Run embedding-based face swap on a video.

    swap_config format:
    {
        "mode": "multi",              # "multi" or "single"
        "source_faces": {             # the NEW AI-generated faces to swap IN
            "person1": "/tmp/face_gen_p1_crop768.jpg",
            "person2": "/tmp/face_gen_p2_crop768.jpg"
        },
        "ref_frames": {              # video-frame references for identity matching
            "person1": "/tmp/young_ref.jpg",
            "person2": "/tmp/older_ref.jpg"
        },
        "similarity_threshold": 0.35  # embedding cosine threshold (optional)
    }

    For single-person mode ("single"):
        "source_faces": {"person1": "/path/to/swap_face.jpg"}
        "ref_frames": omitted (uses simple face_swap like behavior)

    Returns dict matching face_swap_video signature:
        {"success": bool, "total_frames": int, "swapped_frames": int,
         "person_stats": {...}, "output_path": str}
    """
    app, swapper = _get_models()

    # ── Parse config ────────────────────────────────────────────────────
    mode = swap_config.get("mode", "multi")
    source_faces = swap_config.get("source_faces", {})
    ref_frames = swap_config.get("ref_frames", {})
    threshold = swap_config.get("similarity_threshold", 0.35)

    if not source_faces:
        return {"success": False, "error": "No source_faces in swap_config"}

    # ── Load source faces (the NEW faces to swap IN) ────────────────────
    sources = {}  # key -> face_obj
    for key, path in source_faces.items():
        img, face = _load_face(path)
        if face is None:
            return {"success": False, "error": f"No face detected in source: {key} ({path})"}
        sources[key] = face
        gender_str = "F" if face.gender == 0 else "M"
        logger.info("SmartSwap source '%s': age=%d, gender=%s", key, face.age, gender_str)

    # ── Load reference embeddings (for identity matching) ───────────────
    ref_embs = {}  # key -> normed_embedding
    if mode == "multi":
        if not ref_frames:
            return {"success": False, "error": "ref_frames required for multi-person mode"}
        for key, path in ref_frames.items():
            emb = _load_ref_embedding(path)
            if emb is None:
                return {"success": False, "error": f"No face in reference frame: {key} ({path})"}
            ref_embs[key] = emb
        logger.info("SmartSwap multi-person: %d identities, ref keys=%s",
                     len(ref_embs), list(ref_embs.keys()))

    # ── Open video ────────────────────────────────────────────────────
    cap = cv2.VideoCapture(input_video)
    if not cap.isOpened():
        return {"success": False, "error": f"Cannot open video: {input_video}"}

    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if max_frames > 0:
        total = min(total, max_frames)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video, fourcc, fps, (w, h))

    # ── Process frames ────────────────────────────────────────────────
    person_stats = {k: 0 for k in sources}
    person_stats["unmatched"] = 0
    person_stats["no_face"] = 0
    total_swapped = 0

    t0 = time.time()

    for i in range(total):
        ret, frame = cap.read()
        if not ret:
            break

        faces = app.get(frame)

        if not faces:
            person_stats["no_face"] += 1
            out.write(frame)
            continue

        for face in faces:
            if mode == "multi":
                # Match against reference embeddings
                best_key = None
                best_sim = -1
                for key, emb in ref_embs.items():
                    sim = 1 - cosine(face.normed_embedding, emb)
                    if sim > best_sim:
                        best_sim = sim
                        best_key = key

                if best_key is not None and best_sim >= threshold:
                    frame = swapper.get(frame, face, sources[best_key], paste_back=True)
                    person_stats[best_key] += 1
                    total_swapped += 1
                else:
                    # Fallback: use closest source
                    if best_key is not None:
                        frame = swapper.get(frame, face, sources[best_key], paste_back=True)
                        person_stats[best_key] += 1
                        total_swapped += 1
                        person_stats["unmatched"] += 1
                    else:
                        person_stats["no_face"] += 1
            else:
                # Single-person mode: apply first source to all faces
                first_key = list(sources.keys())[0]
                frame = swapper.get(frame, face, sources[first_key], paste_back=True)
                person_stats[first_key] += 1
                total_swapped += 1

        out.write(frame)

        if (i + 1) % 50 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            eta = (total - i - 1) / rate if rate > 0 else 0
            stat_str = " ".join(f"{k}:{v}" for k, v in person_stats.items() if v > 0)
            logger.info("SmartSwap %d/%d (%.0fs, %.0ffps, ETA %.0fs) %s",
                        i + 1, total, elapsed, rate, eta, stat_str)

            if progress_file:
                pct = int((i + 1) / total * 100)
                with open(progress_file, "w") as pf:
                    pf.write(f"{pct}|智能换脸中|{i+1}|{total}|{total_swapped}")

    cap.release()
    out.release()

    elapsed = time.time() - t0
    logger.info("SmartSwap DONE: %.1fs, total_swapped=%d, stats=%s",
                elapsed, total_swapped, person_stats)

    if progress_file and os.path.exists(progress_file):
        try:
            os.remove(progress_file)
        except OSError:
            pass

    return {
        "success": True,
        "total_frames": total,
        "swapped_frames": total_swapped,
        "person_stats": person_stats,
        "output_path": output_video,
    }


# ── Utility: Standalone CLI for clustering identity references ──────

def find_best_reference_frames(video_path: str, step: int = 15, threshold: float = 0.55):
    """
    Scan a video, cluster detected faces by embedding similarity,
    and return the best reference frame for each major identity cluster.
    """
    app, _ = _get_models()
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    all_faces = []
    for i in range(0, total, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            break
        faces = app.get(frame)
        for f in faces:
            g = "F" if f.gender == 0 else "M"
            emb = f.normed_embedding.copy()
            all_faces.append((i, f.age, g, f.det_score, emb, i / fps))

    cap.release()

    clusters = []
    for fn, age, g, det, emb, t in all_faces:
        assigned = False
        for c in clusters:
            sim = 1 - cosine(emb, c[0])
            if sim >= threshold:
                c[1].append((fn, age, g, det, t))
                assigned = True
                break
        if not assigned:
            clusters.append([emb.copy(), [(fn, age, g, det, t)]])

    clusters.sort(key=lambda c: len(c[1]), reverse=True)

    results = []
    for ci, (center, members) in enumerate(clusters):
        best = max(members, key=lambda m: m[3])
        times = [m[4] for m in members]
        ages = [m[1] for m in members]
        genders = set(m[2] for m in members)
        fn_b, ag_b, g_b, de_b, t_b = best
        cluster_info = {
            "cluster": ci + 1,
            "detections": len(members),
            "time_range_s": [round(min(times), 1), round(max(times), 1)],
            "age_range": [min(ages), max(ages)],
            "genders": list(genders),
            "best_frame": fn_b,
            "best_time_sec": round(t_b, 1),
            "best_age": ag_b,
            "best_gender": g_b,
            "best_det_score": round(de_b, 4),
        }
        results.append(cluster_info)
    return results
