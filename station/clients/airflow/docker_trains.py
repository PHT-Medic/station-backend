from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict
import os
from datetime import datetime

from .client import airflow_client
from station.app.crud.crud_docker_trains import docker_trains
from station.app.crud.crud_train_configs import docker_train_config
from station.app.crud.crud_datasets import datasets
from station.clients.minio import MinioClient
from station.app.schemas import docker_trains as dts
from station.app.models import docker_trains as dtm
from loguru import logger

from station.app.config import settings


def run_train(db: Session, train_id: Any, execution_params: dts.DockerTrainExecution) -> dts.DockerTrainSavedExecution:
    """
    Execute a PHT 1.0 docker train using a configured airflow instance

    :param db: database session
    :param train_id: identifier of the train
    :param execution_params: given config_id or config_json can be used for running train
    :return:
    """
    # Extract the train from the database
    db_train = docker_trains.get_by_train_id(db, train_id)
    if not db_train:
        raise HTTPException(status_code=404, detail=f"Train with id '{train_id}' not found.")

    # Use default config if there is no config defined.
    if execution_params is None:
        config_id = db_train.config_id
        if not config_id:
            config_id = "default"
            logger.info("No config defined. Default config is used.")
        execution_params = dts.DockerTrainExecution(config_id=config_id)

    config_dict = validate_run_config(db, train_id, execution_params)

    # Execute the train using the airflow rest api
    try:
        run_id = airflow_client.trigger_dag("run_pht_train", config=config_dict["config"])
        db_train = update_train(db, db_train, run_id, config_dict["config_id"])
        last_execution = db_train.executions[-1]
        return last_execution
    except Exception as e:
        logger.error(f"Error while running train {train_id} with config {config_dict['config']} \n {e}")
        raise HTTPException(status_code=503, detail="No connection to the airflow client could be established.")


def validate_run_config(
        db: Session,
        train_id: str,
        execution_params: dts.DockerTrainExecution) -> dts.DockerTrainAirflowConfig:
    """
    Validate the config used for the triggered run
    :param db: database session
    :param train_id: train id of the train to run
    :param execution_params: includes the config_id of the config to use or the specified config
    :return:
    """
    # Extract config by id if given
    if execution_params.config_id != "default":
        config_general = docker_train_config.get(db, execution_params.config_id)
        print(dts.DockerTrainConfig.from_orm(config_general))

    # Using the default config
    else:
        logger.info(f"Starting train {train_id} using default config")
        # Default config specifies only the identifier of the the train image and uses the latest tag
        harbor_url = settings.config.registry.address
        project = settings.config.registry.project
        config = {
            "repository": f"{harbor_url}/{project}/{train_id}",
            "tag": "latest"
        }
        config_id = None

    if config["repository"] is None or config["tag"] is None:
        raise HTTPException(status_code=400, detail="Train run parameters are missing.")

    return {"config": config, "config_id": config_id}


def update_state(db: Session, db_train, run_time) -> dts.DockerTrainState:
    """
    Update the train state object corresponding to the train
    :param db: database session
    :param db_train: train object
    :param run_time: time when run is triggered
    :return: train state object
    """
    train_state = db.query(dtm.DockerTrainState).filter(dtm.DockerTrainState.train_id == db_train.id).first()
    if train_state:
        train_state.last_execution = run_time
        train_state.num_executions += 1
        train_state.status = 'active'
    else:
        logger.info("No train state assigned.")
    db.add(train_state)
    db.commit()
    db.refresh(train_state)

    return train_state


def update_train(db: Session, db_train, run_id: str, config_id: int) -> dts.DockerTrain:
    """
    Update train parameters
    :param config_id: config id to save for execution
    :param db: database session
    :param db_train: db_train object to update
    :param run_id: run_id of the triggered run
    :return:
    """
    db_train.is_active = True
    run_time = datetime.now()
    db_train.updated_at = run_time

    # Update the train state
    train_state = update_state(db, db_train, run_time)

    # Create an execution
    execution = dtm.DockerTrainExecution(train_id=db_train.id, airflow_dag_run=run_id, config=config_id)
    db.add(execution)
    db.commit()
    db.refresh(execution)

    db.commit()

    return db_train
