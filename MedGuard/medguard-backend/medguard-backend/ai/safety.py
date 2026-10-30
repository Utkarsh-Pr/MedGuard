"""Deterministic safety decision policy. Positive results require all evidence."""

from datetime import date, datetime

from ai.catalog import normalize_name


def get_current_time_slot(now: datetime) -> str:
    if 5 <= now.hour < 12: return "morning"
    if 12 <= now.hour < 17: return "afternoon"
    if 17 <= now.hour < 21: return "evening"
    return "night"


def _expired(expiry_date: str | None) -> bool:
    try:
        return datetime.strptime(expiry_date or "", "%Y-%m-%d").date() < date.today()
    except ValueError:
        return False


def decide_safety(classifier: dict, ocr: dict, quality: dict, prescriptions: list, now: datetime | None = None) -> dict:
    """Return an explainable non-clinical decision with strict precedence."""
    if quality["retake_required"]:
        return {"status": "RETAKE_REQUIRED", "message": "Photo quality is too poor to trust. Retake it in even light without glare.", "matched": None, "reasons": quality["reasons"]}
    if _expired(ocr.get("expiry_date")):
        return {"status": "EXPIRED", "message": "The printed expiry date indicates this medicine is expired. Do not use it; ask a pharmacist.", "matched": None, "reasons": ["expired_medicine"]}
    if classifier["is_unknown"]:
        return {"status": "MANUAL_VERIFICATION", "message": "The strip is not confidently recognized. Please verify it with a pharmacist or a clearer photo.", "matched": None, "reasons": [classifier["reason"]]}
    if not ocr.get("is_legible") or not ocr.get("expiry_date"):
        return {"status": "MANUAL_VERIFICATION", "message": "The printed details are incomplete or unreadable, so this result cannot be verified.", "matched": None, "reasons": ocr.get("failure_reasons", [])}
    predicted = classifier["label"]
    text_name = ocr.get("medicine_name")
    if text_name and normalize_name(text_name) != normalize_name(predicted):
        return {"status": "MANUAL_VERIFICATION", "message": "Image identification and printed label disagree. Verify the strip manually before taking it.", "matched": None, "reasons": ["cnn_ocr_identity_conflict"]}
    matched = next((p for p in prescriptions if normalize_name(p.medicine_name) == normalize_name(predicted)), None)
    if not matched:
        if prescriptions:
            return {"status": "WRONG_MEDICINE", "message": "This recognized medicine does not match your saved prescription. Please verify it before taking it.", "matched": None, "reasons": ["does_not_match_saved_prescriptions"]}
        return {"status": "NOT_ON_LIST", "message": "There are no saved prescriptions to compare with this medicine. Please verify it before taking it.", "matched": None, "reasons": ["no_prescriptions_saved"]}
    slot = get_current_time_slot(now or datetime.now())
    scheduled = [item.strip() for item in matched.time.split(",") if item.strip()]
    if slot not in scheduled:
        return {"status": "WRONG_TIME", "message": f"This appears to match your prescription, but it is not scheduled for {slot}. Check your schedule.", "matched": matched, "reasons": ["outside_scheduled_time"]}
    return {"status": "ADVISORY_MATCH", "message": "This appears to match your prescription and scheduled time. This is an advisory check, not medical authorization.", "matched": matched, "reasons": []}
