import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import UploadFile
from .base import CRUDBase, CreateSchemaType, ModelType

from station.app.models.local_trains import LocalTrain
from station.app.schemas.local_trains import LocalTrainCreate, LocalTrainUpdate
from station.app.local_train_minio.LocalTrainMinIO import train_data


class CRUDLocalTrain(CRUDBase[LocalTrain, LocalTrainCreate, LocalTrainUpdate]):
    def create(self, db: Session, *, obj_in: LocalTrainCreate) -> ModelType:
        if obj_in == None:
            train = LocalTrain(train_id=uuid.uuid4())
        else:
            train = LocalTrain(
                train_id=obj_in.train_id
            )
        db.add(train)
        db.commit()
        db.refresh(train)
        return train

    def remove_train(self, db: Session, train_id: str) -> ModelType:
        # remove minIo entry
        # remove sql database entry
        obj = db.query(LocalTrain).filter(LocalTrain.train_id == train_id).all()
        if not obj:
            return f"train_id {train_id} dose not exit"
        db.delete(obj[0])
        db.commit()
        return obj

    def update_config_add_repostory(self, db: Session, train_id: str, repository: str):
        """
        add a config json to the train database entry
        """
        obj = db.query(LocalTrain).filter(LocalTrain.train_id == train_id).all()[0]
        old_cofig = obj.airflow_config_json
        # TODO change with env
        harbor_url = "harbor-pht.tada5hi.net"
        if old_cofig is None:
            config = self._new_cofig(train_id)
        else:
            config = old_cofig

        config["repository"] = f"{harbor_url}/{repository}"
        self._update_config(db, train_id, config)
        return config

    def update_config_add_tag(self, db: Session, train_id: str, tag: str):
        """
        add a config json to the train database entry
        """
        obj = db.query(LocalTrain).filter(LocalTrain.train_id == train_id).all()[0]
        old_cofig = obj.airflow_config_json
        if old_cofig is None:
            config = self._new_cofig(train_id)
        else:
            config = old_cofig

        config["tag"] = f"{tag}"
        self._update_config(db, train_id, config)
        return config

    def _update_config(self, db, train_id, config):
        db.query(LocalTrain).filter(LocalTrain.train_id == train_id).update({"updated_at": datetime.now()})
        db.query(LocalTrain).filter(LocalTrain.train_id == train_id).update({"airflow_config_json": config})
        db.commit()

    def _new_cofig(self, train_id: str):
        return {
            "repository": None,
            "tag": None,
            "env": None,
            "volumes": None,
            "train_id": train_id
        }

    async def add_file_minio(self, upload_file: UploadFile, train_id: str):

        await train_data.store_train_file(upload_file, train_id)

    def get_all_uploaded_files(self, train_id: str):
        return train_data.get_all_uploaded_files_train(train_id)


    def get_trains(self, db: Session):
        trains = db.query(LocalTrain).all()
        return trains

    def get_train_status(self, db: Session, train_id: str):
        obj = db.query(LocalTrain).filter(LocalTrain.train_id == train_id).all()
        return obj

    def get_train_config(self, db: Session, train_id: str):
        obj = db.query(LocalTrain).filter(LocalTrain.train_id == train_id).all()[0]
        config = obj.airflow_config_json
        return config


local_train = CRUDLocalTrain(LocalTrain)