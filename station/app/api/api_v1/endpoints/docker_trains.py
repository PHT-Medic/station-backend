from typing import List
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException

from station.app.api import dependencies
from station.clients.airflow import docker_trains
from station.app.schemas.docker_trains import DockerTrain, DockerTrainCreate, DockerTrainConfig, \
    DockerTrainConfigCreate, DockerTrainConfigUpdate, DockerTrainExecution
from station.app.crud.crud_docker_trains import docker_train
from station.app.crud.crud_train_configs import docker_train_config

router = APIRouter()


@router.get("/trains/docker", response_model=List[DockerTrain])
def get_available_trains(limit: int = 0, db: Session = Depends(dependencies.get_db)):
    if limit != 0:
        db_trains = docker_train.get_multi(db, limit=limit)
    else:
        db_trains = docker_train.get_multi(db)
    return db_trains


@router.post("/trains/docker", response_model=DockerTrain)
def register_train(create_msg: DockerTrainCreate, db: Session = Depends(dependencies.get_db)):
    if docker_train.get_by_train_id(db, train_id=create_msg.train_id):
        raise HTTPException(status_code=400, detail=f"Train with id '{create_msg.train_id}' already exists.")
    db_train = docker_train.create(db, obj_in=create_msg)
    return db_train


@router.get("/trains/docker/{train_id}", response_model=DockerTrain)
def get_train_by_train_id(train_id: str, db: Session = Depends(dependencies.get_db)):
    db_train = docker_train.get_by_train_id(db, train_id)
    if not db_train:
        raise HTTPException(status_code=404, detail=f"Train with id '{train_id}' not found.")
    return db_train


@router.post("/trains/docker/{train_id}/run")
def run_docker_train(train_id: str, run_config: DockerTrainExecution, db: Session = Depends(dependencies.get_db)):
    # todo check with tyra
    run_id = docker_trains.run_train(db, train_id, run_config)
    return run_id


@router.get("/trains/docker/{train_id}/run")
def get_latest_train_execution_result(train_id: str, db: Session = Depends(dependencies.get_db)):
    # TODO get execution details from db or airflow -> use airflow client
    pass


@router.get("/trains/docker/{train_id}/config", response_model=DockerTrainConfig)
def get_config_for_train(train_id: str, db: Session = Depends(dependencies.get_db)):
    train = docker_train.get_by_train_id(db, train_id)
    if not train.config:
        raise HTTPException(status_code=404, detail=f"Train '{train_id}' does not have an assigned config.")
    return train.config


@router.post("/trains/docker/{train_id}/config/{config_id}", response_model=DockerTrain)
def assign_config_to_docker_train(train_id: str, config_id: int, db: Session = Depends(dependencies.get_db)):
    train = docker_train.get_by_train_id(db, train_id=train_id)
    if not train:
        raise HTTPException(status_code=404, detail=f"Train with id '{train_id}' not found.")

    config = docker_train_config.get(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Config with id '{config_id}' not found.")

    train = docker_train_config.assign_to_train(db, train_id, config.id)
    return train


@router.get("/trains/docker/{train_id}/state")
def get_state_for_train(train_id: str, db: Session = Depends(dependencies.get_db)):
    pass


@router.get("/trains/docker/configs/all", response_model=List[DockerTrainConfig])
def get_all_docker_train_configs(db: Session = Depends(dependencies.get_db), skip: int = 0, limit: int = 100):
    db_configs = docker_train_config.get_multi(db, skip=skip, limit=limit)
    return db_configs


@router.post("/trains/docker/config", response_model=DockerTrainConfig)
def add_docker_train_configuration(config_in: DockerTrainConfigCreate, db: Session = Depends(dependencies.get_db)):
    if docker_train_config.get_by_name(db, name=config_in.name):
        raise HTTPException(status_code=400, detail="A config with the given name already exists.")
    config = docker_train_config.create(db, obj_in=config_in)
    return config


@router.put("/trains/docker/config/{config_id}", response_model=DockerTrainConfig)
def update_docker_train_configuration(update_config: DockerTrainConfigUpdate, config_id: int,
                                      db: Session = Depends(dependencies.get_db)):
    old_config = docker_train_config.get(db, config_id)
    if not old_config:
        raise HTTPException(status_code=404, detail=f"Config with id '{config_id}' not found.")
    config = docker_train_config.update(db, db_obj=old_config, obj_in=update_config)
    return config


@router.get("/trains/docker/config/{config_id}", response_model=DockerTrainConfig)
def get_docker_train_configuration(config_id: int, db: Session = Depends(dependencies.get_db)):
    config = docker_train_config.get(db, config_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Config with id '{config_id}' not found.")

    return config
