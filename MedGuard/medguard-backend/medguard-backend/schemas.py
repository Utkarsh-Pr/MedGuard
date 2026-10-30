"""
schemas.py
----------
Pydantic models define the shape of data going IN to the API
(request bodies) and OUT of the API (responses). FastAPI uses
these to validate requests automatically and to generate the
Swagger docs at /docs.

Note on "time": the frontend sends/receives it as a list, e.g.
["morning", "evening"]. We store it in PostgreSQL as a single
comma-separated string ("morning,evening") for simplicity —
crud.py converts between the two forms.
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


# ---------- Patient ----------

class PatientLogin(BaseModel):
    name: str


class PatientOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True  # allows returning SQLAlchemy objects directly


# ---------- Prescription ----------

class PrescriptionBase(BaseModel):
    medicine_name: str
    strength: str
    tablets: int
    time: List[str]            # e.g. ["morning", "night"]
    frequency: str
    start_date: date
    end_date: date


class PrescriptionCreate(PrescriptionBase):
    patient_id: int


class PrescriptionUpdate(PrescriptionBase):
    """Used for PUT /prescriptions/{id} — all fields are re-sent together."""
    pass


class PrescriptionOut(PrescriptionBase):
    id: int
    patient_id: int

    class Config:
        from_attributes = True


# ---------- Scan history ----------

class ScanHistoryCreate(BaseModel):
    """Used by POST /history if the frontend ever wants to add an entry directly."""
    patient_id: int
    detected_medicine: Optional[str] = None
    confidence: Optional[float] = None
    dosage: Optional[str] = None
    expiry_date: Optional[str] = None
    image_quality: Optional[str] = None
    safety_status: str


class ScanHistoryOut(BaseModel):
    id: int
    patient_id: int
    detected_medicine: Optional[str]
    confidence: Optional[float]
    dosage: Optional[str]
    expiry_date: Optional[str]
    image_quality: Optional[str]
    safety_status: str
    scan_time: datetime

    class Config:
        from_attributes = True


# ---------- Scan result (returned by POST /scan) ----------
# This shape matches what the frontend's result.html page already
# expects (see js/result.js): classifier, ocr, imageQuality, status,
# message, reasons, and matchedPrescription.

class OcrDetails(BaseModel):
    rawText: str
    medicineName: Optional[str] = None
    composition: Optional[str] = None
    dosage: Optional[str] = None
    expiryDate: Optional[str] = None
    batchNumber: Optional[str] = None
    confidence: float
    isLegible: bool
    failureReasons: List[str]


class ClassifierDetails(BaseModel):
    label: str
    confidence: float
    margin: float
    isUnknown: bool
    reason: Optional[str] = None
    catalogVersion: Optional[str] = None


class ImageQualityDetails(BaseModel):
    isAcceptable: bool
    retakeRequired: bool
    reasons: List[str]
    metrics: dict


class MatchedPrescriptionOut(BaseModel):
    name: str
    dosage: str
    time: List[str]
    frequency: str


class ScanResult(BaseModel):
    timestamp: str
    status: str                # ADVISORY_MATCH / WRONG_MEDICINE / WRONG_TIME / NOT_ON_LIST / EXPIRED / RETAKE_REQUIRED / MANUAL_VERIFICATION
    detectedName: Optional[str]
    confidence: float
    classifier: ClassifierDetails
    ocr: OcrDetails
    imageQuality: ImageQualityDetails
    matchedPrescription: Optional[MatchedPrescriptionOut]
    message: str
    reasons: List[str]
