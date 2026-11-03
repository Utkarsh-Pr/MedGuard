"""Medicine-strip inference with a reliable local PyTorch backend."""

import json
import os
from pathlib import Path

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(os.getenv("MEDGUARD_MODEL_PATH", BASE_DIR / "models" / "medicine_classifier.onnx"))
CHECKPOINT_PATH = Path(os.getenv("MEDGUARD_CHECKPOINT_PATH", BASE_DIR / "models" / "medicine_classifier.pt"))
LABELS_PATH = Path(os.getenv("MEDGUARD_LABELS_PATH", BASE_DIR / "models" / "labels.json"))
CALIBRATION_PATH = Path(os.getenv("MEDGUARD_CALIBRATION_PATH", BASE_DIR / "models" / "calibration.json"))
INFERENCE_BACKEND = os.getenv("MEDGUARD_INFERENCE_BACKEND", "onnx").lower()
_model = None
_session = None
_model_error = None


class ModelUnavailable(RuntimeError):
    """Raised when a requested inference backend cannot serve a scan."""


def _softmax(values):
    values = values - np.max(values)
    exps = np.exp(values)
    return exps / np.sum(exps)


def _preprocess_numpy(image_path):
    from PIL import Image
    image = Image.open(image_path).convert("RGB").resize((224, 224))
    pixels = np.asarray(image, dtype=np.float32) / 255.0
    pixels = (pixels - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
    return np.transpose(pixels, (2, 0, 1))[None, ...].astype(np.float32)


def _load_torch_model():
    global _model, _model_error
    if _model is not None:
        return _model
    if _model_error:
        raise ModelUnavailable(_model_error)
    try:
        if not (CHECKPOINT_PATH.exists() and LABELS_PATH.exists()):
            raise FileNotFoundError("PyTorch checkpoint or labels file is missing")
        import torch
        from torchvision import models
        checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu", weights_only=True)
        labels = checkpoint.get("labels") or json.loads(LABELS_PATH.read_text(encoding="utf-8"))
        model = models.mobilenet_v3_small(weights=None)
        model.classifier[3] = torch.nn.Linear(model.classifier[3].in_features, len(labels))
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        _model = (model, labels, torch)
        return _model
    except Exception as error:
        _model_error = f"torch_model_unavailable: {error}"
        raise ModelUnavailable(_model_error) from error


def _load_onnx_session():
    global _session, _model_error
    if _session is not None:
        return _session
    if _model_error:
        raise ModelUnavailable(_model_error)
    try:
        if not (MODEL_PATH.exists() and LABELS_PATH.exists()):
            raise FileNotFoundError("ONNX model or labels file is missing")
        import onnxruntime as ort
        _session = ort.InferenceSession(str(MODEL_PATH), providers=["CPUExecutionProvider"])
        return _session
    except Exception as error:
        _model_error = f"onnx_model_unavailable: {error}"
        raise ModelUnavailable(_model_error) from error


def model_status():
    try:
        if INFERENCE_BACKEND == "torch":
            _, labels, _ = _load_torch_model()
        elif INFERENCE_BACKEND == "onnx":
            _load_onnx_session()
            labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
        else:
            raise ModelUnavailable(f"unsupported_backend: {INFERENCE_BACKEND}")
        return {"backend": INFERENCE_BACKEND, "ready": True, "labels": len(labels), "calibrated": CALIBRATION_PATH.exists(), "error": None}
    except ModelUnavailable as error:
        return {"backend": INFERENCE_BACKEND, "ready": False, "labels": 0, "calibrated": CALIBRATION_PATH.exists(), "error": str(error)}


def _prediction_from_logits(logits, labels):
    probabilities = _softmax(np.asarray(logits, dtype=np.float32))
    order = np.argsort(probabilities)[::-1]
    top, second = int(order[0]), int(order[1])
    return labels[top], float(probabilities[top] * 100), float((probabilities[top] - probabilities[second]) * 100)


def classify_medicine(image_path):
    """Return calibrated identity or explicitly experimental model evidence."""
    if INFERENCE_BACKEND == "torch":
        model, labels, torch = _load_torch_model()
        try:
            tensor = torch.from_numpy(_preprocess_numpy(image_path))
            with torch.inference_mode():
                logits = model(tensor).cpu().numpy()[0]
        except Exception as error:
            raise ModelUnavailable(f"torch_inference_failed: {error}") from error
    elif INFERENCE_BACKEND == "onnx":
        session = _load_onnx_session()
        labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
        try:
            logits = session.run(None, {session.get_inputs()[0].name: _preprocess_numpy(image_path)})[0][0]
        except Exception as error:
            raise ModelUnavailable(f"onnx_inference_failed: {error}") from error
    else:
        raise ModelUnavailable(f"unsupported_backend: {INFERENCE_BACKEND}")

    experimental_label, confidence, margin = _prediction_from_logits(logits, labels)
    if not CALIBRATION_PATH.exists():
        return {"label": "unknown", "experimental_label": experimental_label, "confidence": round(confidence, 2), "margin": round(margin, 2), "is_unknown": True, "reason": "unknown_calibration_missing", "catalog_version": None}
    calibration = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    accepted = confidence >= float(calibration["min_confidence"]) and margin >= float(calibration["min_margin"])
    return {"label": experimental_label if accepted else "unknown", "experimental_label": experimental_label, "confidence": round(confidence, 2), "margin": round(margin, 2), "is_unknown": not accepted, "reason": None if accepted else "below_calibrated_acceptance_threshold", "catalog_version": calibration.get("catalog_version")}
