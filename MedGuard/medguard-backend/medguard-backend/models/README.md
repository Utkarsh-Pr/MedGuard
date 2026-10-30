# Inference artifacts

Production scanning requires all three versioned artifacts in this folder:

- `medicine_classifier.onnx` — MobileNetV3 model exported from the training run
- `labels.json` — ordered labels matching the ONNX output indices
- `calibration.json` — thresholds from `scripts/calibrate_unknown.py`

If any artifact is absent or invalid, MedGuard deliberately returns `unknown`
and `MANUAL_VERIFICATION`. Never ship placeholder thresholds as if validated.
