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
    # ...existing fields...
    CaissonNumber: str | None = None
    IP_1: str | None = None
    IP_2: str | None = None
    SN_SBG1: str | None = None
    SN_Septentrio1: str | None = None
    SN_Ant1: str | None = None
    SN_Ant2: str | None = None
    SN_SBG2: str | None = None
    SN_Septentrio2: str | None = None
    SN_Ant3: str | None = None
    SN_Ant4: str | None = None
