import datetime
import uuid
from fastapi import FastAPI, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import base64

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

# --- File Transfer Schemas ---
class DownloadFileRequest(BaseModel):
    file_path: str

class UploadFileRequest(BaseModel):
    file_path: str
    content: str # Base64 encoded content


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

# --- API Endpoints ---

@app.post("/api/register", response_model=DeviceSchema)
def register_device(device: DeviceCreate, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host
    new_id = str(uuid.uuid4())
    db_device = models.Device(
        id=new_id, name=device.name, ip_address=client_ip,
        registered_at=datetime.datetime.utcnow(), last_seen=datetime.datetime.utcnow()
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    # Explicitly convert SQLAlchemy object to dictionary for Pydantic validation
    return {
        "id": db_device.id,
        "name": db_device.name,
        "ip_address": db_device.ip_address,
        "registered_at": db_device.registered_at,
        "last_seen": db_device.last_seen,
    }

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
    devices = db.query(models.Device).all()
    # Explicitly convert SQLAlchemy objects to dictionaries for Pydantic validation
    return [
        {
            "id": device.id,
            "name": device.name,
            "ip_address": device.ip_address,
            "registered_at": device.registered_at,
            "last_seen": device.last_seen,
        }
        for device in devices
    ]

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
    # Explicitly convert SQLAlchemy object to dictionary for Pydantic validation
    return {
        "id": db_task.id,
        "device_id": db_task.device_id,
        "command": db_task.command,
        "status": db_task.status,
        "created_at": db_task.created_at,
    }

@app.get("/api/tasks/{device_id}", response_model=List[TaskSchema])
def get_all_tasks_for_device(device_id: str, db: Session = Depends(get_db)):
    """Get all tasks (pending, sent, completed) for a specific device."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    tasks = db.query(models.Task).filter(models.Task.device_id == device_id).order_by(models.Task.created_at.desc()).all()
    # Explicitly convert SQLAlchemy objects to dictionaries for Pydantic validation
    return [
        {
            "id": task.id,
            "device_id": task.device_id,
            "command": task.command,
            "status": task.status,
            "created_at": task.created_at,
        }
        for task in tasks
    ]

@app.get("/api/commands/{device_id}", response_model=List[TaskSchema])
def get_commands(device_id: str, db: Session = Depends(get_db)):
    """Get pending commands for a device."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Update last_seen timestamp as a heartbeat
    device.last_seen = datetime.datetime.utcnow()
    
    tasks = db.query(models.Task).filter(
        models.Task.device_id == device_id,
        models.Task.status == "pending"
    ).order_by(models.Task.created_at).all()
    
    # Change status to "sent" to avoid re-execution
    for task in tasks:
        task.status = "sent"

    db.commit()
    # Explicitly convert SQLAlchemy objects to dictionaries for Pydantic validation
    return [
        {
            "id": task.id,
            "device_id": task.device_id,
            "command": task.command,
            "status": task.status,
            "created_at": task.created_at,
        }
        for task in tasks
    ]

@app.post("/api/results/{device_id}", response_model=ResultSchema)
def submit_result(device_id: str, result: ResultCreate, db: Session = Depends(get_db)):
    """Submit results for a completed task."""
    task = db.query(models.Task).filter(models.Task.id == result.task_id).first()
    if not task or task.device_id != device_id:
        raise HTTPException(status_code=404, detail="Task not found or does not belong to this device")

    task.status = "completed"
    
    # Special handling for c2_download results
    if task.command.startswith("c2_download"):
        try:
            download_result = json.loads(result.output)
            if "file_path" in download_result and "content" in download_result:
                if task.id in file_transfer_data:
                    file_transfer_data[task.id]["content"] = download_result["content"]
                    file_transfer_data[task.id]["status"] = "completed"
        except json.JSONDecodeError:
            # If it's a c2_download but not valid JSON, treat as regular output
            pass

    db_result = models.Result(
        device_id=device_id,
        task_id=result.task_id,
        output=result.output
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    # Explicitly convert SQLAlchemy object to dictionary for Pydantic validation
    return {
        "id": db_result.id,
        "device_id": db_result.device_id,
        "task_id": db_result.task_id,
        "output": db_result.output,
        "created_at": db_result.created_at,
    }

@app.get("/api/results/{device_id}", response_model=List[ResultSchema])
def get_results(device_id: str, db: Session = Depends(get_db)):
    """Get all results for a specific device."""
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    results = db.query(models.Result).filter(models.Result.device_id == device_id).order_by(models.Result.created_at.desc()).all()
    # Explicitly convert SQLAlchemy objects to dictionaries for Pydantic validation
    return [
        {
            "id": result.id,
            "device_id": result.device_id,
            "task_id": result.task_id,
            "output": result.output,
            "created_at": result.created_at,
        }
        for result in results
    ]

# --- File Transfer Endpoints ---
@app.post("/api/file/download/{device_id}")
async def request_file_download(device_id: str, request: DownloadFileRequest, db: Session = Depends(get_db)):
    """Requests a file download from the device."""
    db_device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Create a task for the client to download the file
    command = f"c2_download {request.file_path}"
    db_task = models.Task(device_id=device_id, command=command, status="pending")
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    # Store a placeholder for the result, which the client will fill
    file_transfer_data[db_task.id] = {"status": "pending", "content": None}

    # Poll for the result (this is a simplified blocking approach for demonstration)
    # In a real-world scenario, you might use websockets or a more sophisticated polling
    timeout = 30 # seconds
    start_time = datetime.datetime.utcnow()
    while (datetime.datetime.utcnow() - start_time).total_seconds() < timeout:
        if file_transfer_data[db_task.id]["status"] == "completed":
            content = file_transfer_data[db_task.id]["content"]
            del file_transfer_data[db_task.id] # Clean up
            return {"file_path": request.file_path, "content": content}
        await asyncio.sleep(1) # Use asyncio.sleep for non-blocking wait

    del file_transfer_data[db_task.id] # Clean up on timeout
    raise HTTPException(status_code=504, detail="File download timed out or client did not respond.")

@app.post("/api/file/upload/{device_id}")
async def request_file_upload(device_id: str, request: UploadFileRequest, db: Session = Depends(get_db)):
    """Requests a file upload to the device."""
    db_device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not db_device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Create a task for the client to upload the file
    # The command includes the base64 encoded content
    command = f"c2_upload {request.file_path} {request.content}"
    db_task = models.Task(device_id=device_id, command=command, status="pending")
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return {"status": "upload task created", "task_id": db_task.id}

# --- Screen Mirroring ---
from fastapi import Body, Response
import io

# In-memory store for the latest screen frames
latest_screens = {}





@app.post("/api/screen/{device_id}")
async def receive_screen_frame(device_id: str, body: bytes = Body(...)):
    """Receives a screen frame from a device."""
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")
    latest_screens[device_id] = body
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