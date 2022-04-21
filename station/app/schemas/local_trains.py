from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DBSchema(BaseModel):
    class Config:
        orm_mode = True


class LocalTrainBase(BaseModel):
    train_id: str
    train_name: str


class LocalTrainRun(BaseModel):
    train_id: str
    run_id: str


class LocalTrain(DBSchema):
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    train_id: Optional[str] = None
    config_id: Optional[int] = None


class LocalTrainCreate(BaseModel):
    train_name: Optional[str] = None


class LocalTrainConfigBase(BaseModel):
    name: str
    image: Optional[str] = None
    tag: Optional[str] = None
    query: Optional[str] = None
    entrypoint: Optional[str] = None
    volumes: Optional[str] = None
    env: Optional[str] = None
    train_id: Optional[str] = None


class LocalTrainConfigCreate(LocalTrainConfigBase):
    pass


class LocalTrainConfigUpdate(LocalTrainConfigBase):
    pass


class LocalTrainAirflowConfig(BaseModel):
    image: Optional[str] = None
    repository: Optional[str] = None
    tag: Optional[str] = None
    env: Optional[str] = None
    query: Optional[str] = None
    entrypoint: Optional[str] = None
    volumes: Optional[str] = None
    train_id: Optional[str] = None


class LocalTrainInfo(BaseModel):
    id: str
    train_id: str
    train_name: str
    config_id: Optional[str]
    airflow_config_json: Optional[LocalTrainAirflowConfig]
    created_at: datetime
    updated_at: Optional[datetime]
    is_active: bool


class LocalTrainAirflowConfigs(BaseModel):
    configs: Optional[list[LocalTrainAirflowConfig]]


class LocalTrainGetFile(BaseModel):
    train_id: str
    file_name: str


class LocalTrainFile(BaseModel):
    file: str


class MinIOFile(BaseModel):
    bucket_name: str
    object_name: str
    last_modified: datetime
    size: str


class AllFilesTrain(BaseModel):
    files: list[MinIOFile]


class MasterImagesList(BaseModel):
    images: list[str]


class LocalTrainUpdate(LocalTrainCreate):
    pass


class LocalTrainUploadTrainFileResponse(BaseModel):
    train_id: str
    filename: str


class LocalTrainDeleteTrainFileResponse(LocalTrainUploadTrainFileResponse):
    pass


class LocalTrainLog(BaseModel):
    run_id: str
    log: str
