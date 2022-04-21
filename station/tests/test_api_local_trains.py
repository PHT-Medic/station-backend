import pytest
import os
import ast
from fastapi.testclient import TestClient
import json
from station.app.main import app
from station.app.api.dependencies import get_db
import time
from .test_db import override_get_db

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# test general geters
def test_get_master_images():
    response = client.get("/api/localTrains/masterImages")
    assert response.status_code == 200, response.json


def test_get_all_local_trains():
    response = client.get("/api/localTrains")
    assert response.status_code == 200, response.json


@pytest.fixture
def local_train():
    train_creation_response = client.post("api/localTrains")
    assert train_creation_response.status_code == 200, train_creation_response.json
    train_creation_response_dict = json.loads(train_creation_response.text)
    return train_creation_response_dict


@pytest.fixture
def config():
    create_config_response = client.post(
        f"/api/localTrains/config",
        json={
            "name": "test_config",
            "image": "test",
            "tag": "latest",
            "env": None,
            "query": None,
            "entrypoint": "entrypoint.py",
            "volumes": None,
        }
    )
    assert create_config_response.status_code == 200
    config_dict = json.loads(create_config_response.text)
    return config_dict


def test_get_configs(config):
    response = client.get("/api/localTrains/configs")
    assert response.status_code == 200, response.json
    delete_config_response = client.delete("/api/localTrains/config/test_config")
    assert delete_config_response.status_code == 200



def test_getting_local_train_informaion(local_train):
    get_info_response = client.get(f"api/localTrains/{local_train['train_id']}/info")
    assert get_info_response.status_code == 200


def test_change_query_in_config(config):
    query = "test_2"
    get_config_response_before = client.get("/api/localTrains/config/test_config")
    assert get_config_response_before.status_code == 200
    config = json.loads(get_config_response_before.text)
    config["query"] = query
    config["name"] = "test_config"
    put_config_response = client.put(
        f"/api/localTrains/config/test_config",
        json=config
    )
    assert put_config_response.status_code == 200
    get_config_response_after = client.get("/api/localTrains/config/test_config")
    assert get_config_response_after.status_code == 200
    assert json.loads(get_config_response_after.text)["query"] == query
    delete_config_response = client.delete("/api/localTrains/config/test_config")
    assert delete_config_response.status_code == 200


def test_config_changes():
    train_creation_response = client.post("api/localTrains")
    assert train_creation_response.status_code == 200, train_creation_response.json
    train = json.loads(train_creation_response.text)
    create_config_response = client.post(
        f"/api/localTrains/config",
        json={
            "name": "test_config",
            "image": "test",
            "tag": "latest",
            "env": None,
            "query": None,
            "entrypoint": "entrypoint.py",
            "volumes": None,
        }
    )
    assert create_config_response.status_code == 200
    config_dict = json.loads(create_config_response.text)
    assign_config_to_train = client.put(f"/api/localTrains/{train['train_id']}/config/{config_dict['name']}")
    assert assign_config_to_train.status_code == 200
    tag = "test_2"
    get_config_response_before = client.get(f"/api/localTrains/{train['train_id']}/config")
    assert get_config_response_before.status_code == 200
    config = json.loads(get_config_response_before.text)
    config["tag"] = tag
    config["name"] = "test_config"
    put_config_response = client.put(
        f"/api/localTrains/config/{config_dict['name']}",
        json=config
    )
    assert put_config_response.status_code == 200
    get_config_response_after = client.get(f"/api/localTrains/{train['train_id']}/config")
    assert get_config_response_after.status_code == 200
    assert json.loads(get_config_response_after.text)["tag"] == tag
    delete_config_response = client.delete("/api/localTrains/config/test_config")
    assert delete_config_response.status_code == 200


def test_store_and_get_files(local_train):
    if os.getenv("ENVIRONMENT") == "testing":
        entrypoint_name = "entrypoint.py"
        with open(f"./tests/test_files/{entrypoint_name}", "r") as f:
            upload_entrypoint_file_response = client.post(
                f"/api/localTrains/{local_train['train_id']}/files",
                files={"upload_file": ("entrypoint.py", f, "multipart/form-data")}
            )
            assert upload_entrypoint_file_response.status_code == 200, upload_entrypoint_file_response.json

        get_result_response_before_delete = client.get(
            f"api/localTrains/{local_train['train_id']}/file/{entrypoint_name}")
        assert get_result_response_before_delete.status_code == 200, get_result_response_before_delete.json
        delete_file_response = client.delete(f"api/localTrains/{local_train['train_id']}/files/{entrypoint_name}")
        assert delete_file_response.status_code == 200
        get_result_response_after_delete = client.get(
            f"api/localTrains/{local_train['train_id']}/file/{entrypoint_name}")
        assert get_result_response_after_delete.status_code == 200


def test_external_config(local_train):
    create_config_response = client.post(
        f"/api/localTrains/config",
        json={
            "name": "test_config",
            "image": "test",
            "tag": "latest",
            "env": None,
            "query": None,
            "entrypoint": "entrypoint.py",
            "volumes": None,
        }
    )
    assert create_config_response.status_code == 200
    add_config_response = client.put(f"api/localTrains/{local_train['train_id']}/config/test_config")
    assert add_config_response.status_code == 200
    get_info_response_before = client.get(f"api/localTrains/{local_train['train_id']}/info")
    assert get_info_response_before.status_code == 200
    delete_config_response = client.delete(f"api/localTrains/config/test_config")
    assert delete_config_response.status_code == 200
    get_info_response_after = client.get(f"api/localTrains/{local_train['train_id']}/info")
    assert get_info_response_after.status_code == 200


def test_create_and_run_local_train():
    if os.getenv("ENVIRONMENT") == "testing":
        # create local train
        train_creation_response = client.post("api/localTrains", json={"train_name": "testing_local_train"})
        assert train_creation_response.status_code == 200, train_creation_response.json
        train_creation_response_dict = json.loads(train_creation_response.text)

        # configer train train_cration_response.train_id

        create_config_response = client.post(
            f"/api/localTrains/config",
            json={
                "name": "test_config",
                "image": "master/python/base",
                "tag": "latest",
                "env": None,
                "query": None,
                "entrypoint": "entrypoint.py",
                "volumes": None,
            }
        )
        assert create_config_response.status_code == 200
        config_dict = json.loads(create_config_response.text)
        assign_config_to_train = client.put(f"/api/localTrains/{train_creation_response_dict['train_id']}/config/{config_dict['name']}")
        assert assign_config_to_train.status_code == 200


        # upload entrypoint file
        entrypoint_name = "entrypoint.py"
        with open(f"./tests/test_files/{entrypoint_name}", "r") as f:
            upload_entrypoint_file_response = client.post(
                f"/api/localTrains/{train_creation_response_dict['train_id']}/files",
                files={"upload_file": ("entrypoint.py", f, "multipart/form-data")}
            )
            assert upload_entrypoint_file_response.status_code == 200, upload_entrypoint_file_response.json

        # get uploded files and test if entrypoint was stored
        files_uploded_response = client.get(
            f"/api/localTrains/{train_creation_response_dict['train_id']}/files")
        assert files_uploded_response.status_code == 200, files_uploded_response.json
        entrypoint_object_name = json.loads(files_uploded_response.text)["files"][0]["object_name"]
        assert f"{train_creation_response_dict['train_id']}/{entrypoint_name}" == entrypoint_object_name

        # start local train run
        start_train_response = client.post(f"/api/airflow/run_local/run",
                                           json={"train_id": train_creation_response_dict['train_id']})
        assert start_train_response.status_code == 200, start_train_response.json
        run_id = ast.literal_eval(start_train_response.text)["run_id"]

        def run_is_finisted(run_id):
            run_response = client.get(f"/api/airflow/logs/run_local/{run_id}")
            assert run_response.status_code == 200, run_response.json
            run_dict = json.loads(run_response.text)
            task_instances = run_dict["tasklist"]["task_instances"]
            finished_successfully = True
            finished_with_failed_tasks = False
            for task in task_instances:
                finished_successfully = task["state"] == "success" and finished_successfully
                finished_with_failed_tasks = task["state"] == "failed" or finished_with_failed_tasks
            return finished_successfully, finished_with_failed_tasks

        while True:
            finished_successfully, finished_with_failed_tasks = run_is_finisted(run_id)
            assert finished_with_failed_tasks is False
            if finished_successfully:
                break
            time.sleep(10)
            # get uploded files and test if entrypoint was stored
        files_uploded_response = client.get(
            f"/api/localTrains/{train_creation_response_dict['train_id']}/files")
        assert files_uploded_response.status_code == 200, files_uploded_response.json
        # Download files

        # logs
        logs_response = client.get(
            f"/api/localTrains/{train_creation_response_dict['train_id']}/logs" , params={"all_logs": True})
        assert logs_response.status_code == 200
        last_logs_response = client.get(
            f"/api/localTrains/{train_creation_response_dict['train_id']}/logs")
        assert last_logs_response.status_code == 200

        results_object_name = json.loads(files_uploded_response.text)["files"][1]["object_name"]
        assert f"{train_creation_response_dict['train_id']}/results.tar" == results_object_name
        delete_train_response = client.delete(f"/api/localTrains/{train_creation_response_dict['train_id']}")
        assert delete_train_response.status_code == 200
