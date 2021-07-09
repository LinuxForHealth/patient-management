
from pydantic import BaseModel
from typing import Optional

from pydantic.types import Json

fhir_terminology_identifier_type_coding_system = "http://terminology.hl7.org/CodeSystem/v2-0203"


primary_id_type = ['MR', 'PI']

class PatientMasterIndexModel(BaseModel):
    pmidx_id_type: Optional[str]
    pmidx_id_issuer: Optional[str]
    pmidx_id_value: Optional[str]
    pmidx_id_usage: Optional[str]

    def is_primary (self) -> bool:
        return self.pmidx_id_type in primary_id_type

    def get_compound_id(self) -> str:
        return self.pmidx_id_value + '^' + self.pmidx_id_issuer + '^' + self.pmidx_id_type


class PatientMasterIndexModelDbRecord(PatientMasterIndexModel):
    pmidx_id: str
    pmidx_master_idx: Optional[int]

    def get_db_record_list(self) -> str:
        record:str = '"({0},{1},{2},{3},{4},{5})"'\
            .format(self.pmidx_id, self.pmidx_id_type, self.pmidx_id_issuer, self.pmidx_id_value
                    , self.pmidx_id_usage, 0 if self.pmidx_master_idx is None else self.pmidx_master_idx)
        return record

    class Config:
        orm_mode = True

    def update_from_model(self, model:PatientMasterIndexModel):
        if self.pmidx_id != model.get_compound_id():
            raise Exception('Logical Compound Keys do not match')
        self.pmidx_id_type = self.pmidx_id_type if model.pmidx_id_type is None else  model.pmidx_id_type
        self.pmidx_id_issuer = self.pmidx_id_issuer if model.pmidx_id_issuer is None else  model.pmidx_id_issuer
        self.pmidx_id_value = self.pmidx_id_value if model.pmidx_id_value is None else  model.pmidx_id_value
        self.pmidx_id_usage = self.pmidx_id_usage if model.pmidx_id_usage is None else  model.pmidx_id_usage
        return


class PatientMasterIndexLookUpResponse(BaseModel):

    primaryPatientResourceId: str
    primaryPatientResourceEntry : Json