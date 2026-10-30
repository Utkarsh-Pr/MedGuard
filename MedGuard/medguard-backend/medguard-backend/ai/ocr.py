"""English OCR plus deterministic medicine-label field parsing."""

import calendar
import re
from datetime import date

from ai.catalog import catalog_label_in_text

MIN_OCR_CONFIDENCE = 0.60


def _normalize_expiry(month: int, year: int) -> str | None:
    if not 1 <= month <= 12 or not 2020 <= year <= 2100:
        return None
    return date(year, month, calendar.monthrange(year, month)[1]).isoformat()


def parse_medicine_text(raw_text: str, text_confidence: float = 0.0) -> dict:
    text = raw_text or ""
    expiry_match = re.search(r"\b(?:exp(?:iry)?\s*(?:date)?\s*[:.-]?)\s*(0?[1-9]|1[0-2])\s*[/.-]\s*(20\d{2}|\d{2})\b", text, re.I)
    expiry = None
    if expiry_match:
        year = int(expiry_match.group(2)); year += 2000 if year < 100 else 0
        expiry = _normalize_expiry(int(expiry_match.group(1)), year)
    strength_match = re.search(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu)\b", text, re.I)
    batch_match = re.search(r"\b(?:batch|batch no|b\.?\s*no)\s*[:#.-]?\s*([A-Z0-9/-]{3,})", text, re.I)
    failures = []
    if not text.strip(): failures.append("no_text_detected")
    if text_confidence < MIN_OCR_CONFIDENCE: failures.append("low_ocr_confidence")
    if not expiry: failures.append("expiry_not_found")
    return {"raw_text": text, "lines": [line.strip() for line in text.splitlines() if line.strip()],
            "medicine_name": catalog_label_in_text(text), "composition": None,
            "strength": strength_match.group(0) if strength_match else None, "expiry_date": expiry,
            "batch_number": batch_match.group(1) if batch_match else None, "confidence": round(float(text_confidence), 3),
            "is_legible": bool(text.strip()) and text_confidence >= MIN_OCR_CONFIDENCE, "failure_reasons": failures}


def extract_text(image_path: str) -> dict:
    try:
        from paddleocr import PaddleOCR
        global _ocr_engine
        if "_ocr_engine" not in globals():
            _ocr_engine = PaddleOCR(lang="en")
        result = _ocr_engine.ocr(image_path, cls=True)
        lines, confidences = [], []
        for page in result or []:
            for entry in page or []:
                if len(entry) >= 2 and len(entry[1]) >= 2:
                    lines.append(str(entry[1][0]))
                    confidences.append(float(entry[1][1]))
        return parse_medicine_text("\n".join(lines), sum(confidences) / len(confidences) if confidences else 0.0)
    except Exception:
        return parse_medicine_text("", 0.0) | {"failure_reasons": ["ocr_engine_unavailable_or_failed"]}
