from typing import List
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session

from database import Base, engine, get_db
import models
import schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Clinic Management API")


@app.get("/")
def home():
    return {"message": "Clinic Patient Management API is running"}


# ---------- PATIENTS ----------

@app.post("/patients", response_model=schemas.PatientOut)
def add_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    new_patient = models.Patient(**patient.model_dump())
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient


@app.get("/patients", response_model=List[schemas.PatientOut])
def get_patients(db: Session = Depends(get_db)):
    return db.query(models.Patient).all()


# Search /patients/{patient_id} se PEHLE hona zaroori hai
@app.get("/patients/search", response_model=List[schemas.PatientOut])
def search_patients(name: str = None, phone: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Patient)
    if name:
        query = query.filter(models.Patient.name.ilike(f"%{name}%"))
    if phone:
        query = query.filter(models.Patient.phone.contains(phone))
    return query.all()


@app.get("/patients/{patient_id}", response_model=schemas.PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.put("/patients/{patient_id}", response_model=schemas.PatientOut)
def update_patient(patient_id: int, data: schemas.PatientCreate, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    for key, value in data.model_dump().items():
        setattr(patient, key, value)
    db.commit()
    db.refresh(patient)
    return patient


@app.delete("/patients/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    has_appointments = db.query(models.Appointment).filter(
        models.Appointment.patient_id == patient_id
    ).first()
    if has_appointments:
        raise HTTPException(status_code=400, detail="Patient has appointments, cancel them first")
    db.delete(patient)
    db.commit()
    return {"message": "Patient deleted successfully"}


# ---------- DOCTORS ----------

@app.post("/doctors", response_model=schemas.DoctorOut)
def add_doctor(doctor: schemas.DoctorCreate, db: Session = Depends(get_db)):
    new_doctor = models.Doctor(**doctor.model_dump())
    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)
    return new_doctor


@app.get("/doctors", response_model=List[schemas.DoctorOut])
def get_doctors(db: Session = Depends(get_db)):
    return db.query(models.Doctor).all()


# ---------- APPOINTMENTS ----------

@app.post("/appointments", response_model=schemas.AppointmentOut)
def book_appointment(data: schemas.AppointmentCreate, db: Session = Depends(get_db)):
    patient = db.query(models.Patient).filter(models.Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    doctor = db.query(models.Doctor).filter(models.Doctor.id == data.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Double booking check
    clash = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == data.doctor_id,
        models.Appointment.appointment_time == data.appointment_time,
        models.Appointment.status == "booked",
    ).first()
    if clash:
        raise HTTPException(status_code=400, detail="Doctor is already booked at this time")

    appointment = models.Appointment(**data.model_dump())
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@app.get("/appointments", response_model=List[schemas.AppointmentOut])
def get_appointments(db: Session = Depends(get_db)):
    return db.query(models.Appointment).all()


@app.put("/appointments/{appointment_id}/cancel", response_model=schemas.AppointmentOut)
def cancel_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = db.query(models.Appointment).filter(
        models.Appointment.id == appointment_id
    ).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appointment.status = "cancelled"
    db.commit()
    db.refresh(appointment)
    return appointment