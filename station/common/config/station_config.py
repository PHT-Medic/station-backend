import os
from typing import Optional, Union

import yaml
from pydantic import AnyHttpUrl, BaseSettings, validator
from pydantic.env_settings import SettingsSourceCallable
from rich.pretty import pprint

from station.common.config.validators import (
    admin_validator,
    file_readable_validator,
    validate_file_readable,
)
from station.common.constants import ApplicationEnvironment


class StationSettingsConfig:
    """Shared configuration for station settings"""

    use_enum_values = True
    env_prefix: str

    @classmethod
    def with_prefix(cls, prefix: str):
        """Returns a new class with the given prefix"""
        return type(cls.__name__, (cls,), {"env_prefix": prefix})

    @classmethod
    def customise_sources(
        cls,
        init_settings: SettingsSourceCallable,
        env_settings: SettingsSourceCallable,
        file_secret_settings: SettingsSourceCallable,
    ) -> tuple[SettingsSourceCallable, ...]:
        return env_settings, init_settings, file_secret_settings


class StationSettings(BaseSettings):
    """Base Settings with recursive construct method"""

    @classmethod
    def construct(cls, _fields_set=None, **values):
        """Construct a new model object from the function arguments. Recursively construct nested models.
        If an environment variable is available for a field, it will override the value passed in the function
        arguments.

        Args:
            _fields_set: Optional set of fields for hte model
            **values: The values to set for the model

        Returns:
            A new model object
        """
        m = cls.__new__(cls)
        fields_values = {}

        config = cls.__config__

        for name, field in cls.__fields__.items():
            key = field.alias
            if (
                key not in values and config.allow_population_by_field_name
            ):  # Added this to allow population by field name
                key = name

            if key in values:
                if (
                    values[key] is None and not field.required
                ):  # Moved this check since None value can be passed for Optional nested field
                    fields_values[name] = field.get_default()
                else:
                    # check for union type
                    if type(field.type_) == type(Union):
                        print("Found union type")

                    if issubclass(field.type_, BaseSettings):
                        # check if the field is a list of models
                        if field.shape == 2:
                            fields_values[name] = [
                                field.type_.construct(**e) for e in values[key]
                            ]
                        else:
                            fields_values[name] = field.outer_type_.construct(
                                **values[key]
                            )
                    else:
                        fields_values[name] = values[key]
            elif not field.required:
                fields_values[name] = field.get_default()

        # override with env variables
        # read the environment variables specs of the models
        # override the fields only if they are not of object type
        for name, field in m.__fields__.items():
            if issubclass(field.type_, BaseSettings):
                pass
            else:
                env_name = f"{config.env_prefix}{name.upper()}"
                env = os.getenv(env_name)
                if env:
                    # try to convert the value to the type of the field
                    if field.type_ == bool:
                        env = env.lower() == "true"
                    elif field.type_ == int:
                        env = int(env)
                    elif field.type_ == float:
                        env = float(env)
                    # set the value
                    fields_values[name] = env

        object.__setattr__(m, "__dict__", fields_values)
        if _fields_set is None:
            _fields_set = set(values.keys())
        object.__setattr__(m, "__fields_set__", _fields_set)

        m._init_private_attributes()
        return m


class ServiceSettings(StationSettings):
    """Model that contains common settings for configuring the connection to a service
    as admin user.
    """

    admin_user: str
    admin_password: str
    host: str
    port: Optional[int] = None
    # validator for admin password
    _admin_password = admin_validator()

    @staticmethod
    def get_fix(field: str) -> dict[str, str]:
        """Returns a dict with the settings that can be used to fix the service.
        Returns:
            dict: dict with the settings that can be used to fix the service.
        """
        pass


class CentralSettings(StationSettings):
    """Model that contains settings for configuring the connection to the central API as robot user."""

    api_url: AnyHttpUrl
    robot_id: str
    robot_secret: str
    private_key: str
    private_key_password: Optional[str] = None

    Config = StationSettingsConfig.with_prefix("STATION_CENTRAL_")


class HttpSettings(StationSettings):
    """General HTTP settings for the station."""

    port: Optional[int] = 80

    Config = StationSettingsConfig.with_prefix("STATION_HTTP_")


class Certificate(StationSettings):
    """Model that contains settings for configuring the HTTPS certificates."""

    cert: str
    key: str

    _cert_validator = file_readable_validator("cert")
    _key_validator = file_readable_validator("key")

    Config = StationSettingsConfig.with_prefix("STATION_HTTPS_CERTIFICATES_")


class HttpsSettings(StationSettings):
    """MOdel that contains the stations HTTPS settings."""

    port: Optional[int] = 443
    domain: str
    certificate: Optional[Certificate] = None

    Config = StationSettingsConfig.with_prefix("STATION_HTTPS_")


class TraefikSettings(StationSettings):
    """Configuration options for the Stations Traefik instance."""

    dashboard: Optional[bool] = False
    dashboard_port: Optional[int] = 8081

    Config = StationSettingsConfig.with_prefix("STATION_TRAEFIK_")


class RegistrySettings(StationSettings):
    """Model that contains settings for configuring the connection to the central container registry."""

    address: str
    user: str
    password: str
    project: str

    _password = admin_validator("password")

    Config = StationSettingsConfig.with_prefix("STATION_REGISTRY_")


class DBSettings(ServiceSettings):
    """Model that contains settings for configuring the connection to the database."""

    Config = StationSettingsConfig.with_prefix("STATION_DB_")


class AirflowSettings(ServiceSettings):
    """Model that contains settings for configuring the connection to the airflow instance.
    With the option of provididing a custom config and extra DAGs directory.
    """

    config_path: str | None = None
    extra_dags_dir: str | None = None

    @validator("config_path")
    def validate_config_path(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_file_readable(value)

    @validator("extra_dags_dir")
    def validate_extra_dags_dir(cls, value: str | None) -> str | None:
        if value is None:
            return value

        if os.path.isdir(value):
            return value

    Config = StationSettingsConfig.with_prefix("STATION_AIRFLOW_")


class MinioSettings(ServiceSettings):
    """Model that contains settings for configuring the stations minio instance."""

    Config = StationSettingsConfig.with_prefix("STATION_MINIO_")


class AuthSettings(StationSettings):
    """Model that contains settings for configuring the stations authup instance."""

    host: str
    port: Optional[int] = 3001
    admin_user: Optional[str] = "admin"
    robot_id: Optional[str]
    robot_secret: Optional[str]

    Config = StationSettingsConfig.with_prefix("STATION_AUTH_")


class APISettings(StationSettings):
    """Model that contains settings for configuring the station API."""

    port: Optional[int] = 8000
    fernet_key: str
    database: Optional[str] = "pht_station"

    Config = StationSettingsConfig.with_prefix("STATION_API_")

    # todo validate fernet key


class RedisSettings(StationSettings):
    """Model that contains settings for configuring the stations redis instance."""

    host: str
    port: Optional[int] = 6379
    admin_password: Optional[str] = None
    database: Optional[int] = 0

    _admin_password = admin_validator()

    Config = StationSettingsConfig.with_prefix("STATION_REDIS_")


class StationConfig(StationSettings):
    """Unified model that contains all settings for configuring the station."""

    id: str
    environment: ApplicationEnvironment
    admin_password: str
    data_dir: str
    version: str
    central: CentralSettings
    http: HttpSettings
    https: HttpsSettings
    traefik: TraefikSettings
    registry: RegistrySettings
    api: APISettings
    db: DBSettings
    airflow: AirflowSettings
    minio: MinioSettings
    auth: AuthSettings
    redis: RedisSettings

    _admin_password = admin_validator()

    def display(self):
        pprint(self, expand_all=True)

    @classmethod
    def from_file(cls, path: str) -> "StationConfig":
        with open(path, "r") as f:
            # load yaml as dict
            return cls.parse_obj(yaml.safe_load(f))

    Config = StationSettingsConfig.with_prefix("STATION_")
