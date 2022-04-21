from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from station.app.api import dependencies
from station.clients.airflow.client import airflow_client
from station.clients.airflow import docker_trains as airflow_docker_train
from station.app.schemas.airflow import AirflowInformation, AirflowTaskLog, AirflowRun, AirflowRunMsg
from station.app.schemas.local_trains import LocalTrainRun
from station.app.schemas.docker_trains import DockerTrainExecution
from station.app.crud.crud_local_train import local_train
from station.app.crud.crud_docker_trains import docker_trains


router = APIRouter()


@router.post("/{dag_id}/run", response_model=AirflowRun)
def run(run_msg: AirflowRunMsg, dag_id: str, db: Session = Depends(dependencies.get_db)):
    """
    Trigger a dag run and return the run_id of the run
    @param dag_id: ID of the DAG e.G. "run_local" , "run_pht_train" etc.
    @param run_msg: UID of the train
    @param db:  reference to the postgres database
    """

    if dag_id == "run_local":
        config = local_train.get_train_run_config(db, run_msg.train_id)
        run_id = airflow_client.trigger_dag("run_local", config)
        run_information = LocalTrainRun(train_id=run_msg.train_id, run_id=run_id)
        local_train.create_run(db, obj_in=run_information)
        config_id = config["config_id"]
    elif dag_id == "run_pht_train":
        train = docker_trains.get_by_train_id(db, run_msg.train_id)
        if not train.config_id:
            run_config = None
            config_id = "default"
        else:
            run_config = DockerTrainExecution(config_id=train.config_id)
            config_id = train.config_id
        execution = airflow_docker_train.run_train(db, run_msg.train_id, run_config)
        run_id = execution.airflow_dag_run

    else:
        raise HTTPException(status_code=404, detail=f"DAG with id '{dag_id}' not found.")

    return {"run_id": run_id,
            "config_id": config_id,
            "dag_id": dag_id,
            "train_id": run_msg.train_id,
            "start_date": datetime.now()
            }


@router.get("/logs/{dag_id}/{run_id}", response_model=AirflowInformation)
def get_airflow_run_information(run_id: str, dag_id: str):
    """
    Get information about one airflow DAG execution.
    @param dag_id: ID of the DAG e.G. "run_local" , "run_pht_train" etc.
    @param run_id: Airflow run ID
    @return:
    """

    run_info = airflow_client.get_run_information(dag_id, run_id)
    return run_info


@router.get("/logs/{dag_id}/{run_id}/{task_id}", response_model=AirflowTaskLog)
def get_airflow_task_log(dag_id: str, run_id: str, task_id: str, task_try_number: int = None):
    """
    Get log of a task in a DAG execution.
    @param dag_id: ID of the DAG e.G. "run_local" , "run_pht_train" etc.
    @param task_id: id of teh task
    @param run_id: Airflow run ID
    @param task_try_number: specific try number for log request
    @return:
    """
    run_info_data = airflow_client.get_task_log(dag_id, run_id, task_id, task_try_number)
    if not run_info_data:
        raise HTTPException(status_code=404, detail=f"{task_id} not found.")
    return {"run_info": run_info_data}
