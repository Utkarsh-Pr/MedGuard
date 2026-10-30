"""Closed-set ONNX medicine-strip classifier with calibrated unknown gating."""

import json
import os
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(os.getenv("MEDGUARD_MODEL_PATH", BASE_DIR / "models" / "medicine_classifier.onnx"))
LABELS_PATH = Path(os.getenv("MEDGUARD_LABELS_PATH", BASE_DIR / "models" / "labels.json"))
CALIBRATION_PATH = Path(os.getenv("MEDGUARD_CALIBRATION_PATH", BASE_DIR / "models" / "calibration.json"))
_session = None


def _load_artifacts():
    global _session
    if _session is not None:
        return _session
    if not (MODEL_PATH.exists() and LABELS_PATH.exists() and CALIBRATION_PATH.exists()):
        return None
    try:
        import onnxruntime as ort
        _session = ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])
        return _session
    except Exception:
        return None


def _softmax(values):
    values = values - np.max(values)
    exps = np.exp(values)
    return exps / np.sum(exps)


def _preprocess(image_path: str):
    from PIL import Image
    image = Image.open(image_path).convert("RGB").resize((224, 224))
    pixels = np.asarray(image, dtype=np.float32) / 255.0
    pixels = (pixels - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
    return np.transpose(pixels, (2, 0, 1))[None, ...].astype(np.float32)


def classify_medicine(image_path: str) -> dict:
    """Return a label only when calibrated confidence and margin gates both pass."""
    session = _load_artifacts()
    default = {"label": "unknown", "confidence": 0.0, "margin": 0.0, "is_unknown": True,
               "reason": "classifier_model_unavailable", "catalog_version": None}
    if not session:
        return default
    try:
        labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
        calibration = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
        logits = session.run(None, {session.get_inputs()[0].name: _preprocess(image_path)})[0][0]
        probabilities = _softmax(np.asarray(logits, dtype=np.float32))
        order = np.argsort(probabilities)[::-1]
        top, second = int(order[0]), int(order[1])
        confidence, margin = float(probabilities[top] * 100), float((probabilities[top] - probabilities[second]) * 100)
        accepted = confidence >= float(calibration["min_confidence"]) and margin >= float(calibration["min_margin"])
        return {"label": labels[top] if accepted else "unknown", "confidence": round(confidence, 2),
                "margin": round(margin, 2), "is_unknown": not accepted,
                "reason": None if accepted else "below_calibrated_acceptance_threshold",
                "catalog_version": calibration.get("catalog_version")}
    except Exception:
        return default | {"reason": "classifier_inference_failed"}
