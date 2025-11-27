import datetime
import uuid
import secrets # Import secrets module
from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.security import APIKeyHeader # For API Key authentication
from sqlalchemy.orm import Session
from typing import List, Optional

from c2_server import models, database

# Pydantic Schemas for API validation
from pydantic import BaseModel

# --- Device Schemas ---
class DeviceBase(BaseModel):
    name: str
    ip_address: Optional[str] = None

class DeviceCreate(DeviceBase):
    pass

class DeviceSchema(DeviceBase):
    id: str
    api_key: str # Include api_key in the schema
    registered_at: datetime.datetime
    last_seen: datetime.datetime

    class Config:
        from_attributes = True

# --- Task Schemas ---
class TaskBase(BaseModel):
    command: str

class TaskCreate(TaskBase):
    device_id: str

class TaskSchema(TaskBase):
    id: int
    device_id: str
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# --- Result Schemas ---
class ResultBase(BaseModel):
    task_id: int
    output: str

class ResultCreate(ResultBase):
    pass

class ResultSchema(ResultBase):
    id: int
    device_id: str
    created_at: datetime.datetime
    
    class Config:
        from_attributes = True


# --- App Initialization ---
app = FastAPI(title="RaspyjackC2 API")

@app.on_event("startup")
def on_startup():
    database.init_db()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def authenticate_device(api_key: str = Depends(api_key_header), db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.api_key == api_key).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "X-API-Key"},
        )
    return device

# --- API Endpoints ---

@app.post("/api/register", response_model=DeviceSchema)
def register_device(device: DeviceCreate, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host
    new_id = str(uuid.uuid4())
    new_api_key = secrets.token_urlsafe(32) # Generate a secure API key
    db_device = models.Device(
        id=new_id, name=device.name, ip_address=client_ip, api_key=new_api_key,
        registered_at=datetime.datetime.utcnow(), last_seen=datetime.datetime.utcnow()
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

@app.delete("/api/devices/{device_id}")
def delete_device(device_id: str, db: Session = Depends(get_db)):
    """Deletes a device and all of its associated tasks and results."""
    db_device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Manually delete associated results and tasks to ensure cascade
    db.query(models.Result).filter(models.Result.device_id == device_id).delete()
    db.query(models.Task).filter(models.Task.device_id == device_id).delete()
    
    db.delete(db_device)
    db.commit()
    return {"status": "success", "message": f"Device {device_id} and all its data deleted."}

@app.get("/api/devices", response_model=List[DeviceSchema])
def get_devices(db: Session = Depends(get_db)):
    return db.query(models.Device).all()

@app.post("/api/tasks", response_model=TaskSchema)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task for a device."""
    db_device = db.query(models.Device).filter(models.Device.id == task.device_id).first()
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    db_task = models.Task(**task.dict(), status="pending")
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/api/commands", response_model=List[TaskSchema])
def get_commands(device: models.Device = Depends(authenticate_device), db: Session = Depends(get_db)):
    """Get pending commands for a device."""
    # Update last_seen timestamp as a heartbeat
    device.last_seen = datetime.datetime.utcnow()
    
    tasks = db.query(models.Task).filter(
        models.Task.device_id == device.id,
        models.Task.status == "pending"
    ).order_by(models.Task.created_at).all()
    
    # Change status to "sent" to avoid re-execution
    for task in tasks:
        task.status = "sent"

    db.commit()
    return tasks

@app.post("/api/results", response_model=ResultSchema)
def submit_result(result: ResultCreate, device: models.Device = Depends(authenticate_device), db: Session = Depends(get_db)):
    """Submit results for a completed task."""
    task = db.query(models.Task).filter(models.Task.id == result.task_id).first()
    if not task or task.device_id != device.id:
        raise HTTPException(status_code=404, detail="Task not found or does not belong to this device")

    task.status = "completed"
    
    db_result = models.Result(
        device_id=device.id,
        task_id=result.task_id,
        output=result.output
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

@app.get("/api/results/{device_id}", response_model=List[ResultSchema])
def get_results(device_id: str, db: Session = Depends(get_db)):
    """Get all results for a specific device."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    results = db.query(models.Result).filter(models.Result.device_id == device_id).order_by(models.Result.created_at.desc()).all()
    return results

# --- Screen Mirroring ---
from fastapi import Body, Response
import io

# In-memory store for the latest screen frames
latest_screens = {}

@app.post("/api/screen", response_model=dict)
async def receive_screen_frame(body: bytes = Body(...), device: models.Device = Depends(authenticate_device)):
    """Receives a screen frame from a device."""
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")
    latest_screens[device.id] = body
    return {"status": "received"}

@app.get("/api/screen/{device_id}")
async def get_screen_frame(device_id: str):
    """Returns the latest screen frame for a device."""
    if device_id not in latest_screens:
        raise HTTPException(status_code=404, detail="No screen data available for this device.")
    
    frame = latest_screens[device_id]
    return Response(content=frame, media_type="image/jpeg")


# --- Debug Endpoints ---
@app.get("/debug/tasks", response_model=List[TaskSchema])
def debug_get_tasks(db: Session = Depends(get_db)):
    """(Debug) Get all tasks from the database."""
    return db.query(models.Task).order_by(models.Task.created_at.desc()).all()

@app.get("/debug/results", response_model=List[ResultSchema])
def debug_get_results(db: Session = Depends(get_db)):
    """(Debug) Get all results from the database."""
    return db.query(models.Result).order_by(models.Result.created_at.desc()).all()


@app.get("/")
def read_root():
    return {"message": "RaspyjackC2 API is running."}