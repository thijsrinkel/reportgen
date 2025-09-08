from pydantic import BaseModel
from typing import Optional

class JobData(BaseModel):
    # shared / required key
    CaissonNumber: str

    # IPs
    IP_1: Optional[str] = None
    IP_2: Optional[str] = None

    # Serials / antennas
    SN_SBG1: Optional[str] = None
    SN_Septentrio1: Optional[str] = None
    SN_Ant1: Optional[str] = None
    SN_Ant2: Optional[str] = None
    SN_SBG2: Optional[str] = None
    SN_Septentrio2: Optional[str] = None
    SN_Ant3: Optional[str] = None
    SN_Ant4: Optional[str] = None

    # Document refs
    MCRDocumentReference: Optional[str] = None
    DIMCONDocumentReference: Optional[str] = None
    DocumentReference8: Optional[str] = None
    DocumentReference9: Optional[str] = None
