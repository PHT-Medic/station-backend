from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, JSON
from datetime import datetime
from station.app.db.base_class import Base


class LocalTrainState(Base):
    __tablename__ = "local_train_states"
    id = Column(Integer, primary_key=True, index=True)
    train_id = Column(Integer, ForeignKey('local_trains.id'))
    last_execution = Column(DateTime, nullable=True)
    num_executions = Column(Integer, default=0)
    status = Column(String, default="inactive")


class LocalTrainExecution(Base):
    __tablename__ = "local_train_executions"
    id = Column(Integer, primary_key=True, index=True)
    train_id = Column(String, ForeignKey('local_trains.train_id'))
    airflow_dag_run = Column(String, nullable=True, unique=True)
    start = Column(DateTime, default=datetime.now())
    end = Column(DateTime, nullable=True)

class LocalTrainConfig(Base):
    __tablename__ = "local_trains_config"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, nullable=True)
    airflow_config = Column(JSON, nullable=True)

class LocalTrain(Base):
    __tablename__ = "local_trains"
    id = Column(Integer, primary_key=True, index=True)
    train_id = Column(String, unique=True)
    train_name = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, nullable=True)
    config_id = Column(Integer, ForeignKey("local_trains_config.id"), nullable=True)
    is_active = Column(Boolean, default=False)
