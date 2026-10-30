"""Score an ONNX model on known/unknown images for calibration.csv."""
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def preprocess(path):
    image = Image.open(path).convert("RGB").resize((224, 224))
    pixels = np.asarray(image, dtype=np.float32) / 255
    pixels = (pixels - [.485, .456, .406]) / [.229, .224, .225]
    return np.transpose(pixels, (2, 0, 1))[None].astype(np.float32)


def score(logits):
    logits = logits - logits.max(); probabilities = np.exp(logits) / np.exp(logits).sum()
    ranked = np.sort(probabilities)[::-1]
    return round(float(ranked[0] * 100), 4), round(float((ranked[0] - ranked[1]) * 100), 4)


def main(model_path, known_manifest, unknown_dir, output_csv):
    import onnxruntime as ort
    session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    rows = []
    for row in csv.DictReader(Path(known_manifest).open(encoding="utf-8")):
        confidence, margin = score(session.run(None, {input_name: preprocess(row["path"])})[0][0])
        rows.append({"path": row["path"], "confidence": confidence, "margin": margin, "is_known": 1})
    for image in Path(unknown_dir).rglob("*"):
        if image.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            confidence, margin = score(session.run(None, {input_name: preprocess(image)})[0][0])
            rows.append({"path": str(image.resolve()), "confidence": confidence, "margin": margin, "is_known": 0})
    if not any(row["is_known"] == 0 for row in rows): raise SystemExit("Unknown image folder is empty; calibration is unsafe")
    with Path(output_csv).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "confidence", "margin", "is_known"]); writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__": main(*sys.argv[1:])
