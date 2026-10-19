from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Neon database URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Database connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

app = FastAPI()


# Database table
class PatientDB(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    age = Column(Integer)
    phone = Column(String)
    diagnosis = Column(String)


# Create table in Neon
Base.metadata.create_all(bind=engine)


# Pydantic model
class PatientCreate(BaseModel):
    name: str
    age: int
    phone: str
    diagnosis: str


# Home
@app.get("/")
def home():
    return {"message": "Clinic Patient Management API is running"}


# Add patient
@app.post("/patients")
def add_patient(patient: PatientCreate):

    db = SessionLocal()

    new_patient = PatientDB(
        name=patient.name,
        age=patient.age,
        phone=patient.phone,
        diagnosis=patient.diagnosis
    )

    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)

    result = {
        "id": new_patient.id,
        "name": new_patient.name,
        "age": new_patient.age,
        "phone": new_patient.phone,
        "diagnosis": new_patient.diagnosis
    }

    db.close()

    return result


# Get all patients
@app.get("/patients")
def get_patients():

    db = SessionLocal()

    patients = db.query(PatientDB).all()

    result = [
        {
            "id": patient.id,
            "name": patient.name,
            "age": patient.age,
            "phone": patient.phone,
            "diagnosis": patient.diagnosis
        }
        for patient in patients
    ]

    db.close()

    return result


# Get patient by ID
@app.get("/patients/{patient_id}")
def get_patient(patient_id: int):

    db = SessionLocal()

    patient = db.query(PatientDB).filter(
        PatientDB.id == patient_id
    ).first()

    if not patient:
        db.close()
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    result = {
        "id": patient.id,
        "name": patient.name,
        "age": patient.age,
        "phone": patient.phone,
        "diagnosis": patient.diagnosis
    }

    db.close()

    return result


# Update patient
@app.put("/patients/{patient_id}")
def update_patient(patient_id: int, patient: PatientCreate):

    db = SessionLocal()

    existing_patient = db.query(PatientDB).filter(
        PatientDB.id == patient_id
    ).first()

    if not existing_patient:
        db.close()
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    existing_patient.name = patient.name
    existing_patient.age = patient.age
    existing_patient.phone = patient.phone
    existing_patient.diagnosis = patient.diagnosis

    db.commit()
    db.refresh(existing_patient)

    result = {
        "id": existing_patient.id,
        "name": existing_patient.name,
        "age": existing_patient.age,
        "phone": existing_patient.phone,
        "diagnosis": existing_patient.diagnosis
    }

    db.close()

    return result


# Delete patient
@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: int):

    db = SessionLocal()

    patient = db.query(PatientDB).filter(
        PatientDB.id == patient_id
    ).first()

    if not patient:
        db.close()
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    db.delete(patient)
    db.commit()

    db.close()

    return {"message": "Patient deleted successfully"}