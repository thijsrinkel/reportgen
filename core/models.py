# core/models.py
from pydantic import BaseModel
from typing import Optional
from datetime import date

class EquipmentModel(BaseModel):
    Make: Optional[str] = None
    Model: Optional[str] = None
    SerialNumber: Optional[str] = None

class SensorsModel(BaseModel):
    MBES: Optional[EquipmentModel] = None
    INS: Optional[EquipmentModel] = None

class OperatorsModel(BaseModel):
    PartyChief: Optional[str] = None
    Surveyor: Optional[str] = None

class JobData(BaseModel):
    ProjectName: str
    ClientName: Optional[str] = None
    Date: date
    SurveyVessel: Optional[str] = None
    Equipment: Optional[SensorsModel] = None   # ✅ Optional
    Operators: Optional[OperatorsModel] = None # ✅ Optional
    Notes: Optional[str] = None
