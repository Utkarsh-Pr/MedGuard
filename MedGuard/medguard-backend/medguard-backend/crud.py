"""
crud.py
-------
"CRUD" = Create, Read, Update, Delete. This file contains all the
functions that actually talk to the database via SQLAlchemy.
main.py calls these functions instead of writing raw queries
inline, which keeps the API endpoints short and easy to read.
"""

from sqlalchemy.orm import Session

import models
import schemas


# ---------- Helpers: "time" list <-> comma-separated string ----------

def _time_list_to_str(time_list):
    return ",".join(time_list)


def _time_str_to_list(time_str):
    if not time_str:
        return []
    return time_str.split(",")


# ---------- Patients ----------

def get_or_create_patient(db: Session, name: str) -> models.Patient:
    """
    Demo login has no password — we just look up a patient by name,
    and create one if it doesn't exist yet. This keeps the frontend's
    simple "type a name and enter" flow working while still giving
    every patient a real integer ID for foreign keys.
    """
    patient = db.query(models.Patient).filter(models.Patient.name == name).first()
    if patient:
        return patient

    patient = models.Patient(name=name)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def get_patient(db: Session, patient_id: int):
    return db.query(models.Patient).filter(models.Patient.id == patient_id).first()


# ---------- Prescriptions ----------

def create_prescription(db: Session, prescription: schemas.PrescriptionCreate) -> models.Prescription:
    db_prescription = models.Prescription(
        patient_id=prescription.patient_id,
        medicine_name=prescription.medicine_name,
        strength=prescription.strength,
        tablets=prescription.tablets,
        time=_time_list_to_str(prescription.time),
        frequency=prescription.frequency,
        start_date=prescription.start_date,
        end_date=prescription.end_date,
    )
    db.add(db_prescription)
    db.commit()
    db.refresh(db_prescription)
    return db_prescription


def get_prescriptions_for_patient(db: Session, patient_id: int):
    return (
        db.query(models.Prescription)
        .filter(models.Prescription.patient_id == patient_id)
        .all()
    )


def get_prescription(db: Session, prescription_id: int):
    return db.query(models.Prescription).filter(models.Prescription.id == prescription_id).first()


def update_prescription(db: Session, prescription_id: int, updates: schemas.PrescriptionUpdate):
    db_prescription = get_prescription(db, prescription_id)
    if not db_prescription:
        return None

    db_prescription.medicine_name = updates.medicine_name
    db_prescription.strength = updates.strength
    db_prescription.tablets = updates.tablets
    db_prescription.time = _time_list_to_str(updates.time)
    db_prescription.frequency = updates.frequency
    db_prescription.start_date = updates.start_date
    db_prescription.end_date = updates.end_date

    db.commit()
    db.refresh(db_prescription)
    return db_prescription


def delete_prescription(db: Session, prescription_id: int) -> bool:
    db_prescription = get_prescription(db, prescription_id)
    if not db_prescription:
        return False
    db.delete(db_prescription)
    db.commit()
    return True


def prescription_to_dict(prescription: models.Prescription) -> dict:
    """Converts a Prescription ORM object into a plain dict with
    `time` as a list, ready to send back as JSON."""
    return {
        "id": prescription.id,
        "patient_id": prescription.patient_id,
        "medicine_name": prescription.medicine_name,
        "strength": prescription.strength,
        "tablets": prescription.tablets,
        "time": _time_str_to_list(prescription.time),
        "frequency": prescription.frequency,
        "start_date": prescription.start_date,
        "end_date": prescription.end_date,
    }


# ---------- Scan history ----------

def create_scan_history_entry(db: Session, entry: schemas.ScanHistoryCreate) -> models.ScanHistory:
    db_entry = models.ScanHistory(
        patient_id=entry.patient_id,
        detected_medicine=entry.detected_medicine,
        confidence=entry.confidence,
        dosage=entry.dosage,
        expiry_date=entry.expiry_date,
        image_quality=entry.image_quality,
        safety_status=entry.safety_status,
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry


def get_history_for_patient(db: Session, patient_id: int):
    return (
        db.query(models.ScanHistory)
        .filter(models.ScanHistory.patient_id == patient_id)
        .order_by(models.ScanHistory.scan_time.desc())
        .all()
    )
