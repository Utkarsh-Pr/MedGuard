"""English OCR plus deterministic medicine-label field parsing."""

import calendar
import re
from datetime import date

from ai.catalog import catalog_label_in_text

MIN_OCR_CONFIDENCE = 0.60


class OcrEngineUnavailable(RuntimeError):
    """The optional PaddleOCR dependency could not process an image."""


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
        lines, confidences = _run_paddle_ocr(image_path)
        return parse_medicine_text("\n".join(lines), sum(confidences) / len(confidences) if confidences else 0.0)
    except Exception:
        return parse_medicine_text("", 0.0) | {"failure_reasons": ["ocr_engine_unavailable_or_failed"]}


def _run_paddle_ocr(image_path: str) -> tuple[list[str], list[float]]:
    """Run the shared English engine while retaining line-level confidence."""
    try:
        from paddleocr import PaddleOCR
        global _ocr_engine
        if "_ocr_engine" not in globals():
            _ocr_engine = PaddleOCR(lang="en")
        result = _ocr_engine.ocr(image_path, cls=True)
    except Exception as error:
        raise OcrEngineUnavailable(str(error)) from error
    lines, confidences = [], []
    for page in result or []:
        for entry in page or []:
            if len(entry) >= 2 and len(entry[1]) >= 2:
                lines.append(str(entry[1][0]))
                confidences.append(float(entry[1][1]))
    return lines, confidences


_STRENGTH_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu)\b", re.I)
_SCHEDULE_RE = re.compile(r"\b([0-3])\s*[-/]\s*([0-3])\s*[-/]\s*([0-3])\b")
_DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b")
_DURATION_RE = re.compile(r"\bfor\s+(\d{1,3})\s*days?\b", re.I)


def _parse_date(value: str) -> str | None:
    match = _DATE_RE.search(value)
    if not match:
        return None
    try:
        return date(int(match.group(3)), int(match.group(2)), int(match.group(1))).isoformat()
    except ValueError:
        return None


def _frequency_and_times(text: str) -> tuple[str | None, list[str], int | None, list[str]]:
    """Extract only explicit schedule evidence; ambiguous shorthand stays a warning."""
    warnings, times, frequency, tablets = [], [], None, None
    schedule = _SCHEDULE_RE.search(text)
    if schedule:
        amounts = [int(schedule.group(i)) for i in range(1, 4)]
        labels = ["morning", "afternoon", "night"]
        times = [label for label, amount in zip(labels, amounts) if amount > 0]
        non_zero = [amount for amount in amounts if amount > 0]
        if non_zero and len(set(non_zero)) == 1:
            tablets = non_zero[0]
        elif non_zero:
            warnings.append("different tablet quantities by time require review")
        if len(times) == 1: frequency = "Once daily"
        elif len(times) == 2: frequency = "Twice daily"
        elif len(times) == 3: frequency = "Thrice daily"
    else:
        lower = text.lower()
        frequency_map = [(r"\b(?:od|once\s+(?:a\s+)?day|once daily)\b", "Once daily"),
                         (r"\b(?:bd|bid|twice\s+(?:a\s+)?day|twice daily)\b", "Twice daily"),
                         (r"\b(?:tds|tid|thrice\s+(?:a\s+)?day|three times daily)\b", "Thrice daily")]
        for pattern, label in frequency_map:
            if re.search(pattern, lower):
                frequency = label
                warnings.append("frequency shorthand does not specify a time of day")
                break
        for word in ("morning", "afternoon", "evening", "night"):
            if re.search(rf"\b{word}\b", lower): times.append(word)
    return frequency, times, tablets, warnings


def _candidate_name(line: str) -> str | None:
    cleaned = re.sub(r"^\s*(?:s\.?\s*no\.?\s*)?\d+\s*[.)-]\s*", "", line, flags=re.I)
    cleaned = re.sub(r"^\s*(?:tab(?:let)?s?|cap(?:sule)?s?|syrup|inj(?:ection)?)\.?\s*", "", cleaned, flags=re.I)
    cleaned = _STRENGTH_RE.split(cleaned, maxsplit=1)[0]
    cleaned = _SCHEDULE_RE.split(cleaned, maxsplit=1)[0]
    cleaned = re.split(r"\b(?:od|bd|bid|tds|tid|once|twice|thrice|for|after|before|morning|afternoon|evening|night)\b", cleaned, maxsplit=1, flags=re.I)[0]
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" :-,.")
    if not re.search(r"[A-Za-z]{2}", cleaned): return None
    if re.fullmatch(r"(?:rx|date|diagnosis|name|age|patient|doctor|prescription)", cleaned, re.I): return None
    return cleaned


def parse_printed_prescription(lines: list[dict] | list[str], overall_confidence: float | None = None) -> dict:
    """Build an editable draft from printed text; deliberately never guesses fields."""
    normalised = [item if isinstance(item, dict) else {"text": item, "confidence": 0.0} for item in lines]
    text_lines = [str(item.get("text", "")).strip() for item in normalised if str(item.get("text", "")).strip()]
    confidences = [float(item.get("confidence", 0.0)) for item in normalised if str(item.get("text", "")).strip()]
    confidence = float(overall_confidence) if overall_confidence is not None else (sum(confidences) / len(confidences) if confidences else 0.0)
    raw_text = "\n".join(text_lines)
    dates = [_parse_date(line) for line in text_lines]
    def labelled_date(labels: str) -> str | None:
        match = re.search(rf"\b(?:{labels})\b\s*[:.-]?\s*(\d{{1,2}}[/-]\d{{1,2}}[/-]20\d{{2}})", raw_text, re.I)
        return _parse_date(match.group(1)) if match else None
    explicit_start = labelled_date("start|from")
    explicit_end = labelled_date("end|until|till|to")
    if not explicit_start and len([d for d in dates if d]) >= 2: explicit_start, explicit_end = [d for d in dates if d][:2]
    candidates = []
    for item in normalised:
        line = str(item.get("text", "")).strip()
        line_confidence = float(item.get("confidence", 0.0))
        strength = _STRENGTH_RE.search(line)
        marker = re.search(r"\b(?:tab(?:let)?s?|cap(?:sule)?s?|syrup|inj(?:ection)?)\b", line, re.I)
        if not (strength or marker):
            continue
        name = _candidate_name(line)
        if not name:
            continue
        frequency, times, tablets, warnings = _frequency_and_times(line)
        duration = _DURATION_RE.search(line)
        if line_confidence < MIN_OCR_CONFIDENCE: warnings.append("low OCR confidence; verify this row")
        if not times: warnings.append("timing is missing or ambiguous; choose it before saving")
        if not strength: warnings.append("strength is missing; verify before saving")
        candidates.append({"medicine_name": name, "strength": strength.group(0) if strength else None,
                           "tablets": tablets, "time": times, "frequency": frequency,
                           "start_date": explicit_start, "end_date": explicit_end,
                           "course_days": int(duration.group(1)) if duration else None,
                           "instructions": "after meals" if re.search(r"\bafter meals?\b", line, re.I) else None,
                           "confidence": round(line_confidence, 3), "raw_line": line, "warnings": warnings})
    warnings = []
    if not raw_text: warnings.append("no printed text detected; enter the prescription manually")
    if confidence < MIN_OCR_CONFIDENCE: warnings.append("OCR confidence is low; verify every field")
    if not candidates: warnings.append("no medicine rows detected; handwritten prescriptions require manual entry")
    return {"raw_text": raw_text, "confidence": round(confidence, 3), "candidates": candidates, "warnings": warnings}


def extract_prescription_text(image_path: str) -> dict:
    lines, confidences = _run_paddle_ocr(image_path)
    items = [{"text": value, "confidence": score} for value, score in zip(lines, confidences)]
    return parse_printed_prescription(items)
