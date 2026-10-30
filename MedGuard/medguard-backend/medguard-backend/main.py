"""
main.py
-------
The FastAPI application. This is the file you run to start the
backend (`uvicorn main:app --reload`).

It wires everything together:
  - database.py   -> DB connection + get_db()
  - models.py     -> table definitions
  - schemas.py    -> request/response validation
  - crud.py       -> database read/write functions
  - ai/*.py       -> conservative ONNX/OCR/CV evidence pipeline

Endpoints:
  POST   /patients/login          demo login (get-or-create by name)
  POST   /prescriptions           add a prescription
  GET    /prescriptions/{patient_id}  list a patient's prescriptions
  PUT    /prescriptions/{id}      edit a prescription
  DELETE /prescriptions/{id}      remove a prescription
  POST   /scan                    upload a medicine photo, get a safety result
  GET    /history/{patient_id}    list a patient's past scans
  POST   /history                 add a scan-history entry directly
"""

import os
import shutil
import uuid
from datetime import date, datetime
from typing import List

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import crud
import models  # noqa: F401 — imported so Base knows about all the tables below
import schemas
from ai.classifier import classify_medicine
from ai.image_quality import check_image_quality
from ai.ocr import extract_text
from ai.safety import decide_safety
from database import Base, engine, get_db

# ---------------------------------------------------------------
# Create the database tables (if they don't already exist).
# In a bigger project you'd use a migration tool (e.g. Alembic),
# but for a student project this one-liner is enough.
# ---------------------------------------------------------------
Base.metadata.create_all(bind=engine)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="MedGuard API", description="AI-Powered Medication Safety Assistant — backend")

# ---------------------------------------------------------------
# CORS: allows the HTML/JS frontend (opened from a different
# origin, e.g. a "Live Server" on localhost, or even file://) to
# call this API from the browser. Wide open here because this is
# a local student demo, not a public deployment.
# ---------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded images back out, e.g. http://localhost:8000/uploads/xyz.jpg
# (handy for debugging in the browser / Swagger docs).
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# =================================================================
# Patients
# =================================================================

@app.post("/patients/login", response_model=schemas.PatientOut)
def login(patient: schemas.PatientLogin, db: Session = Depends(get_db)):
    """
    Demo login: the frontend just sends a name. If a patient with
    that name already exists we reuse it, otherwise we create one.
    This gives the frontend a real integer patient_id to use for
    everything else (prescriptions, scans, history).
    """
    return crud.get_or_create_patient(db, patient.name)


# =================================================================
# Prescriptions
# =================================================================

@app.post("/prescriptions", response_model=schemas.PrescriptionOut)
def create_prescription(prescription: schemas.PrescriptionCreate, db: Session = Depends(get_db)):
    db_prescription = crud.create_prescription(db, prescription)
    return crud.prescription_to_dict(db_prescription)


@app.get("/prescriptions/{patient_id}", response_model=List[schemas.PrescriptionOut])
def read_prescriptions(patient_id: int, db: Session = Depends(get_db)):
    prescriptions = crud.get_prescriptions_for_patient(db, patient_id)
    return [crud.prescription_to_dict(p) for p in prescriptions]


@app.put("/prescriptions/{prescription_id}", response_model=schemas.PrescriptionOut)
def update_prescription(prescription_id: int, updates: schemas.PrescriptionUpdate, db: Session = Depends(get_db)):
    updated = crud.update_prescription(db, prescription_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return crud.prescription_to_dict(updated)


@app.delete("/prescriptions/{prescription_id}")
def delete_prescription(prescription_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_prescription(db, prescription_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return {"message": "Prescription deleted successfully"}


# =================================================================
# Scan history
# =================================================================

@app.get("/history/{patient_id}", response_model=List[schemas.ScanHistoryOut])
def read_history(patient_id: int, db: Session = Depends(get_db)):
    return crud.get_history_for_patient(db, patient_id)


@app.post("/history", response_model=schemas.ScanHistoryOut)
def add_history_entry(entry: schemas.ScanHistoryCreate, db: Session = Depends(get_db)):
    """Lets the frontend add a scan-history row directly, without going
    through /scan. Not normally needed (POST /scan already saves one
    automatically) but included since the project spec asks for it."""
    return crud.create_scan_history_entry(db, entry)


# =================================================================
# Medicine scanning + safety check
# =================================================================

def process_medicine_image(image_path: str) -> dict:
    """Collect independent image, classifier, and OCR evidence."""
    quality = check_image_quality(image_path)
    # Quality is still captured even when unusable. Avoid expensive OCR/model
    # work when it cannot contribute trusted evidence.
    classification = classify_medicine(image_path) if quality["is_acceptable"] else {"label": "unknown", "confidence": 0.0, "margin": 0.0, "is_unknown": True, "reason": "quality_gate_failed", "catalog_version": None}
    ocr_result = extract_text(image_path) if quality["is_acceptable"] else {"raw_text": "", "medicine_name": None, "composition": None, "strength": None, "expiry_date": None, "batch_number": None, "confidence": 0.0, "is_legible": False, "failure_reasons": ["quality_gate_failed"]}
    return {"quality": quality, "classifier": classification, "ocr": ocr_result}


@app.post("/scan", response_model=schemas.ScanResult)
async def scan_medicine(
    patient_id: int = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Accepts a medicine photo + patient_id from the Scan page.
    Runs the quality, ONNX-classifier, and OCR pipeline, compares the result with
    the patient's prescriptions, saves the outcome to scan_history,
    and returns a result shaped exactly like the frontend expects
    (see js/result.js).
    """
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Save the uploaded image to disk with a unique filename.
    file_extension = os.path.splitext(image.filename or "")[1] or ".jpg"
    saved_filename = f"{uuid.uuid4().hex}{file_extension}"
    saved_path = os.path.join(UPLOAD_DIR, saved_filename)

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # ---- Step A: collect model/OCR/quality evidence ----
    ai_result = process_medicine_image(saved_path)

    # ---- Step B: conservative rule-based decision against saved prescriptions ----
    prescriptions = crud.get_prescriptions_for_patient(db, patient_id)
    decision = decide_safety(ai_result["classifier"], ai_result["ocr"], ai_result["quality"], prescriptions)
    status, message, matched = decision["status"], decision["message"], decision["matched"]

    # ---- Step C: save this scan to history ----
    history_entry = schemas.ScanHistoryCreate(
        patient_id=patient_id,
        detected_medicine=None if ai_result["classifier"]["is_unknown"] else ai_result["classifier"]["label"],
        confidence=ai_result["classifier"]["confidence"],
        dosage=ai_result["ocr"]["strength"],
        expiry_date=ai_result["ocr"]["expiry_date"],
        image_quality="Retake required" if ai_result["quality"]["retake_required"] else "Acceptable",
        safety_status=status,
    )
    crud.create_scan_history_entry(db, history_entry)

    # ---- Step D: build the response the frontend expects ----
    matched_out = None
    if matched:
        matched_out = schemas.MatchedPrescriptionOut(
            name=matched.medicine_name,
            dosage=matched.strength,
            time=crud._time_str_to_list(matched.time),
            frequency=matched.frequency,
        )

    return schemas.ScanResult(
        timestamp=datetime.utcnow().isoformat(),
        status=status,
        detectedName=None if ai_result["classifier"]["is_unknown"] else ai_result["classifier"]["label"],
        confidence=ai_result["classifier"]["confidence"],
        classifier=schemas.ClassifierDetails(label=ai_result["classifier"]["label"], confidence=ai_result["classifier"]["confidence"], margin=ai_result["classifier"]["margin"], isUnknown=ai_result["classifier"]["is_unknown"], reason=ai_result["classifier"]["reason"], catalogVersion=ai_result["classifier"]["catalog_version"]),
        ocr=schemas.OcrDetails(rawText=ai_result["ocr"]["raw_text"], medicineName=ai_result["ocr"]["medicine_name"], composition=ai_result["ocr"]["composition"], dosage=ai_result["ocr"]["strength"], expiryDate=ai_result["ocr"]["expiry_date"], batchNumber=ai_result["ocr"]["batch_number"], confidence=ai_result["ocr"]["confidence"], isLegible=ai_result["ocr"]["is_legible"], failureReasons=ai_result["ocr"]["failure_reasons"]),
        imageQuality=schemas.ImageQualityDetails(isAcceptable=ai_result["quality"]["is_acceptable"], retakeRequired=ai_result["quality"]["retake_required"], reasons=ai_result["quality"]["reasons"], metrics=ai_result["quality"]["metrics"]),
        matchedPrescription=matched_out,
        message=message,
        reasons=decision["reasons"],
    )


@app.get("/")
def root():
    """A tiny health-check route — visiting http://localhost:8000 should show this."""
    return {"message": "MedGuard API is running. Visit /docs for interactive API docs."}
