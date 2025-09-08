from pydantic import BaseModel
from typing import Optional

class JobData(BaseModel):
    CaissonNumber: str

    IP_1: Optional[str] = None
    IP_2: Optional[str] = None

    SN_SBG1: Optional[str] = None
    SN_Septentrio1: Optional[str] = None
    SN_Ant1: Optional[str] = None
    SN_Ant2: Optional[str] = None

    SN_SBG2: Optional[str] = None
    SN_Septentrio2: Optional[str] = None
    SN_Ant3: Optional[str] = None
    SN_Ant4: Optional[str] = None
