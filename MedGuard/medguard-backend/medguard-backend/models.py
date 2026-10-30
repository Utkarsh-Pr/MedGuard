"""
models.py
---------
SQLAlchemy ORM models — each class here becomes one table in
PostgreSQL. Run main.py once (it calls Base.metadata.create_all)
and these tables will be created automatically.
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Patient(Base):
    """
    A very simple patient/user record. The demo login page just
    asks for a name — there's no password, this is a college
    major-project demo, not a real authentication system.
    """
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    prescriptions = relationship("Prescription", back_populates="patient", cascade="all, delete")
    scans = relationship("ScanHistory", back_populates="patient", cascade="all, delete")


class Prescription(Base):
    """
    One medicine entry from the doctor's prescription, entered
    manually on the Prescription page (no OCR involved here).
    """
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    medicine_name = Column(String, nullable=False)
    strength = Column(String, nullable=False)          # e.g. "500 mg"
    tablets = Column(Integer, nullable=False)           # tablets per dose
    time = Column(String, nullable=False)                # stored as "morning,evening"
    frequency = Column(String, nullable=False)           # e.g. "Twice daily"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    patient = relationship("Patient", back_populates="prescriptions")


class ScanHistory(Base):
    """
    One past medicine scan and its safety-check result.
    Created automatically whenever POST /scan runs, and also
    available to add manually via POST /history.
    """
    __tablename__ = "scan_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    detected_medicine = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    dosage = Column(String, nullable=True)
    expiry_date = Column(String, nullable=True)         # kept as text: OCR may fail to read it
    image_quality = Column(String, nullable=True)
    safety_status = Column(String, nullable=False)       # advisory/verification status from ai.safety
    scan_time = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="scans")
