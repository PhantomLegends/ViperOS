import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    passcode_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    failure_policy = Column(String, default="stop") # "stop" or "continue"
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    actions = relationship("WorkflowAction", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowAction(Base):
    __tablename__ = "workflow_actions"
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    order = Column(Integer, nullable=False)
    type = Column(String, nullable=False) # e.g., launch_app, open_url
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    workflow = relationship("Workflow", back_populates="actions")

class CommandLog(Base):
    __tablename__ = "command_logs"
    id = Column(Integer, primary_key=True, index=True)
    command = Column(String, nullable=False)
    result = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(String, nullable=False)

class PendingConfirmation(Base):
    __tablename__ = "pending_confirmations"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)
    payload = Column(Text, nullable=True)
    expiration_time = Column(DateTime, nullable=False)