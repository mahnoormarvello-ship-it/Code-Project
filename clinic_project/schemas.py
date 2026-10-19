from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class PatientCreate(BaseModel):
    name: str
    age: int
    phone: str
    diagnosis: str


class PatientOut(PatientCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class DoctorCreate(BaseModel):
    name: str
    specialization: str


class DoctorOut(DoctorCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_time: datetime
    reason: str

    @field_validator("appointment_time", mode="before")
    @classmethod
    def parse_am_pm(cls, v):
        if isinstance(v, str):
            for fmt in ("%Y-%m-%d %I:%M %p", "%Y-%m-%d %I:%M%p"):
                try:
                    return datetime.strptime(v.strip().upper(), fmt)
                except ValueError:
                    pass
        return v


class AppointmentOut(AppointmentCreate):
    id: int
    status: str
    model_config = ConfigDict(from_attributes=True)