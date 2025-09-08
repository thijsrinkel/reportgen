# core/models.py
from pydantic import BaseModel
from typing import Optional
from datetime import date

class Equipment(BaseModel):
    Make: Optional[str] = None
    Model: Optional[str] = None
    SerialNumber: Optional[str] = None

class Sensors(BaseModel):
    MBES: Optional[Equipment] = None
    INS: Optional[Equipment] = None

class Operators(BaseModel):
    PartyChief: Optional[str] = None
    Surveyor: Optional[str] = None

class JobData(BaseModel):
    ProjectName: str
    ClientName: Optional[str] = None
    Date: date
    SurveyVessel: Optional[str] = None
    Equipment: Optional[Sensors] = None
    Operators: Optional[Operators] = None
    Notes: Optional[str] = None
