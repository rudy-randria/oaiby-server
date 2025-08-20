from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class SystemInfo(BaseModel):
    """Informations générales du système"""
    hostname: str
    os: str
    architecture: str
    boot_time: datetime
    uptime: float

class SystemLoad(BaseModel):
    """Charge système"""
    load_1min: float
    load_5min: float
    load_15min: float
    cpu_count: int

class ProcessInfo(BaseModel):
    """Informations d'un processus"""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str
    create_time: datetime
    user: Optional[str] = None
    cmdline: Optional[List[str]] = None

class SystemAction(BaseModel):
    """Action système (reboot, shutdown)"""
    action: str
    delay: Optional[int] = 0  # délai en secondes
    message: Optional[str] = None