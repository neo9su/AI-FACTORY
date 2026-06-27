#!/usr/bin/env python3
"""Find best reference frames for each identity by scanning full video."""
import cv2, numpy as np
from insightface.app import FaceAnalysis
from scipy.spatial.distance import cosine

app = FaceAnalysis(name="buffalo_l", root="/home/neo/.insightface/models",
                   providers=["CUDAExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))

# Check extracted frames first with correct mapping
for fnum, actual_frame, label in [
    (1, 45, "young host expected"),
    (2, 300, "young host"),
    (3, 555, "older host expected"),
    (4, 600, "older host"),
    (5, 900, "young returns"),
]:
    path = "/tmp/check_frame_%d.jpg" % fnum
    img = cv2.imread(path)
    if img is None:
        print("  check_frame_%d (actual frame %d, %s): NOT FOUND" % (fnum, actual_frame, label))
        continue
    faces = app.get(img)
    if not faces:
        print("  check_frame_%d (actual frame %d, %s): NO FACE" % (fnum, actual_frame, label))
        continue
    f = faces[0]
    g = "F" if f.gender == 0 else "M"
    print("  check_frame_%d (actual=%d, %s): %d face(s), age=%d, %s, det=%.4f" % (
        fnum, actual_frame, label, len(faces), f.age, g, f.det_score))

# Now scan full video for best references
print("\n=== Scanning full video ===")
cap = cv2.VideoCapture("/home/neo/autonomous-ai-factory/videos/千万別再用脏洗衣机洗衣服了_source_clean_dub.mp4")
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)

all_faces = []
step = 15
for i in range(0, total, step):
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ret, frame = cap.read()
    if not ret:
        break
    faces = app.get(frame)
    for f in faces:
        g = "F" if f.gender == 0 else "M"
        emb = f.normed_embedding.copy()
        all_faces.append((i, f.age, g, f.det_score, emb, i/fps))

cap.release()
print("  Sampled %d face detections from %d sample frames" % (len(all_faces), total // step + 1))

# Simple clustering: each detection compared against existing cluster centers
clusters = []
THRESH = 0.55

for fn, age, g, det, emb, t in all_faces:
    assigned = False
    for c in clusters:
        sim = 1 - cosine(emb, c[0])
        if sim >= THRESH:
            c[1].append((fn, age, g, det, t))
            assigned = True
            break
    if not assigned:
        clusters.append([emb.copy(), [(fn, age, g, det, t)]])

# Sort by size
clusters.sort(key=lambda c: len(c[1]), reverse=True)

for ci, (center, members) in enumerate(clusters[:6]):
    print("\n  Cluster %d: %d detections" % (ci + 1, len(members)))
    best = max(members, key=lambda m: m[3])
    times = [m[4] for m in members]
    ages = [m[1] for m in members]
    genders = set(m[2] for m in members)
    print("    Time range: %.1fs - %.1fs" % (min(times), max(times)))
    print("    Age range: %d - %d" % (min(ages), max(ages)))
    print("    Genders: %s" % ", ".join(sorted(genders)))
    fn_best, age_best, g_best, det_best, t_best = best
    print("    Best frame: #%d @ %.1fs (age=%d, %s, det=%.4f)" % (fn_best, t_best, age_best, g_best, det_best))
    print("    Top 5 frames by det_score:")
    top5 = sorted(members, key=lambda m: m[3], reverse=True)[:5]
    for fn, age, g, det, t in top5:
        print("      #%d @ %.1fs (age=%d, %s, det=%.4f)" % (fn, t, age, g, det))
