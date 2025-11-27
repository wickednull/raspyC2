import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base

class Device(Base):
    __tablename__ = "devices"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    ip_address = Column(String)
    api_key = Column(String, unique=True, index=True) # New API Key field
    registered_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)

    tasks = relationship("Task", back_populates="device")
    results = relationship("Result", back_populates="device")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.id"))
    command = Column(String)
    status = Column(String, default="pending") # pending, sent, completed
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    device = relationship("Device", back_populates="tasks")

class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))
    output = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    device = relationship("Device", back_populates="results")
