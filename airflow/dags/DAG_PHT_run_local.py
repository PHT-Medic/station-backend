from pprint import pprint
import asyncio
import tarfile
import os
import time
from io import BytesIO
import shutil
import docker
from airflow.decorators import dag, task
from airflow.operators.python import get_current_context
from airflow.utils.dates import days_ago

from train_lib.clients import PHTFhirClient
from station.clients.minio import MinioClient

# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization


TRAIN_PATH = "/opt/pht_train"
RESULT_PATH = "/opt/pht_results"

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
}


@dag(default_args=default_args, schedule_interval=None, start_date=days_ago(2), tags=['pht', 'train'])
def run_local():
    """
    Defins a DAG simular to the run train only for local execution of test Trains dosent contain any of the sequrety
    and stores the restults not ecripted into the minIO.
    @return:
    """

    @task()
    def get_train_configuration() -> dict:
        """
        extra the train state dict form airflow context

        @return: train_state_dict
        """
        context = get_current_context()
        repository, tag, env, entrypoint, volumes, query, train_id, run_id = [context['dag_run'].conf.get(_, None) for _
                                                                              in
                                                                              ['repository', 'tag', 'env', 'entrypoint',
                                                                               'volumes', 'query', 'train_id',
                                                                               'run_id']]
        img = repository + ":" + tag

        # TODO Schemas for train config - returns the dict
        # train_state = LocalTrainState.from_context(context)

        train_state_dict = {
            "repository": repository,
            "train_id": train_id,
            "tag": tag,
            "img": img,
            "env": env,
            "volumes": volumes,
            "query": query,
            "entrypoint": entrypoint,
            "build_dir": "./temp/",
            "bucket_name": "localtrain",
            "run_id": context['dag_run'].run_id
        }
        return train_state_dict

    @task()
    def pull_docker_image(train_state_dict) -> dict:
        """
        pull the master Image from harbor

        @param train_state_dict:
        @return: train_state_dict
        """
        docker_client = docker.from_env()
        harbor_address = os.getenv("HARBOR_URL")
        docker_client.login(username=os.getenv("HARBOR_USER"), password=os.getenv("HARBOR_PW"),
                            registry=harbor_address)
        docker_client.images.pull(repository=train_state_dict["repository"], tag=train_state_dict["tag"])

        return train_state_dict

    @task()
    def build_train(train_state_dict) -> dict:
        """
        Build the train by extracting the entrypoint from minIO and adding it to the pulled image

        @param train_state_dict:
        @return:
        """
        # create minIO client
        docker_client = docker.from_env()
        minio_client = MinioClient()
        # create the docker File like object that can be added to the master image
        docker_file = f'''
                            FROM {train_state_dict["img"]}
                            RUN mkdir {RESULT_PATH}
                            RUN mkdir {TRAIN_PATH}
                            RUN chmod -R +x {TRAIN_PATH}
                            CMD ["python", "{TRAIN_PATH}/{train_state_dict['entrypoint']}"]
                            '''
        docker_file = BytesIO(docker_file.encode("utf-8"))

        # create docker container
        image, logs = docker_client.images.build(fileobj=docker_file)
        container = docker_client.containers.create(image.id)

        # load the entrypoint form minIO into to a local tar file
        entrypoint = minio_client.get_file(train_state_dict["bucket_name"],
                                           f"{train_state_dict['train_id']}/{train_state_dict['entrypoint']}")

        name = train_state_dict['entrypoint']
        archive_obj = BytesIO()
        tar = tarfile.TarFile(fileobj=archive_obj, mode='w')
        endpoint_info = tarfile.TarInfo(name)
        endpoint_info.size = len(entrypoint)
        endpoint_info.mtime = time.time()
        tar.addfile(endpoint_info, BytesIO(entrypoint))
        tar.close()
        archive_obj.seek(0)
        container.put_archive(TRAIN_PATH, archive_obj)
        container.wait()
        container.commit(repository="local_train", tag="latest")
        container.wait()
        return train_state_dict

    @task()
    def execute_query(train_state_dict) -> dict:
        """
        if a query is defind in the train parameters, the query file is loaded  and executed in the same way
        as the normal trains.
        the query results are saved localy into the AIRFLOW_DATA_DIR if exists(if not "/opt/station_data")
        The train_state_dict gets updateted with the enviroment variabls and the volume information for the data folder

        @param dict train_state_dict: train parameters
        @return: dict train_state_dict: train parameters
        """
        # check if a query is defined
        if train_state_dict["query"] is None:
            return train_state_dict
        # try to cache errors and save to logs
        try:
            query = train_state_dict.get("query", None)
            if query:
                print("Query found, setting up connection to FHIR server")

                env_dict = train_state_dict.get("env", None)
                if env_dict:
                    fhir_url = env_dict.get("FHIR_ADDRESS", None)
                    # Check that there is a FHIR server specified in the configuration dictionary
                    if fhir_url:
                        fhir_client = PHTFhirClient.from_dict(env_dict)

                    else:
                        fhir_client = PHTFhirClient.from_env()
                else:
                    fhir_client = PHTFhirClient.from_env()

                query_result = fhir_client.execute_query(query=train_state_dict["query"])

                output_file_name = query["data"]["filename"]

                # Create the file path in which to store the FHIR query results
                data_dir = os.getenv("AIRFLOW_DATA_DIR", "/opt/station_data")
                train_data_dir = os.path.join(data_dir, train_state_dict["train_id"])

                if not os.path.isdir(train_data_dir):
                    os.mkdir(train_data_dir)

                train_data_dir = os.path.abspath(train_data_dir)
                print("train data dir: ", train_data_dir)

                train_data_path = fhir_client.store_query_results(query_result, storage_dir=train_data_dir,
                                                                  filename=output_file_name)
                print("train data path: ", train_data_path)
                host_data_path = os.path.join(os.getenv("STATION_DATA_DIR"), train_state_dict["train_id"],
                                              output_file_name)

                # Add the file containing the fhir query results to the volumes configuration
                query_data_volume = {
                    host_data_path: {
                        "bind": f"/opt/train_data/{output_file_name}",
                        "mode": "ro"
                    }
                }

                data_dir_env = {
                    "TRAIN_DATA_PATH": f"/opt/train_data/{output_file_name}"
                }

                if isinstance(train_state_dict.get("volumes"), dict):
                    train_state_dict["volumes"] = {**query_data_volume, **train_state_dict["volumes"]}
                else:
                    train_state_dict["volumes"] = query_data_volume

                if train_state_dict.get("env", None):
                    train_state_dict["env"] = {**train_state_dict["env"], **data_dir_env}
                else:
                    train_state_dict["env"] = data_dir_env
        except Exception as e:
            # save logs for errors that happened during query execution
            with open(f'{train_state_dict["build_dir"]}log.txt', 'a+') as f:
                f.write(e)
                print(f"logs_query_start({e})logs_end")

        return train_state_dict

    @task()
    def run_train(train_state_dict) -> dict:
        """
        The container gets executed with the environment variables and volumes
        whait

        @param dict train_state_dict: train parameters
        @return: dict train_state_dict: train parameters
        """
        docker_client = docker.from_env()

        environment = train_state_dict.get("env", {})
        volumes = train_state_dict.get("volumes", {})
        container = docker_client.containers.run("local_train", environment=environment, volumes=volumes,
                                                 detach=True)
        container.wait()
        bits, stat = container.get_archive(RESULT_PATH)
        results = BytesIO()
        for chunk in bits:
            results.write(chunk)
        results.seek(0)

        minio_client = MinioClient()
        asyncio.run(
            minio_client.store_files(bucket=train_state_dict["bucket_name"],
                                     name=f"{train_state_dict['train_id']}/results.tar", file=results))

        if not os.path.isdir(train_state_dict["build_dir"]):
            os.mkdir(train_state_dict["build_dir"])
        logs = container.logs().decode("utf-8")
        print(f"logs_container_start({logs})logs_end")
        with open(f'{train_state_dict["build_dir"]}log.txt', 'a+') as f:
            f.write(logs)

        container.remove(v=True, force=True)
        return train_state_dict

    @task()
    def save_results(train_state_dict) -> dict:
        """
        Stores the results and logs form the container inot minIO

        @param dict train_state_dict: train parameters
        @return: dict train_state_dict: train parameters
        """

        minio_client = MinioClient()

        # Store logs
        with open(f'{train_state_dict["build_dir"]}log.txt', 'rb') as logs:
            asyncio.run(
                minio_client.store_files(bucket=train_state_dict["bucket_name"],
                                         name=f"{train_state_dict['train_id']}/{train_state_dict['run_id']}/log.",
                                         file=logs))

        return train_state_dict

    @task()
    def clean_up(train_state_dict):
        """
        Remove all temporary data form the build dir

        @param dict train_state_dict: train parameters
        @return:
        """
        try:
            shutil.rmtree(str(train_state_dict["build_dir"]))
        except OSError as e:
            print("Error: %s - %s." % (e.filename, e.strerror))

        # TODO add the removeing or storage of query results

    local_train = get_train_configuration()
    local_train = pull_docker_image(local_train)
    local_train = build_train(local_train)
    local_train = execute_query(local_train)
    local_train = run_train(local_train)
    local_train = save_results(local_train)
    clean_up(local_train)


run_local = run_local()
