from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from enum import Enum

class ServiceAction(str, Enum):
    """Actions possibles sur un service"""
    START = "start"
    STOP = "stop"
    RESTART = "restart"
    RELOAD = "reload"
    ENABLE = "enable"
    DISABLE = "disable"
    STATUS = "status"

class ServiceStatus(str, Enum):
    """États possibles d'un service"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    ACTIVATING = "activating"
    DEACTIVATING = "deactivating"
    UNKNOWN = "unknown"

class ServiceManageRequest(BaseModel):
    """Requête de gestion d'un service"""
    service_name: str = Field(..., regex=r'^[a-zA-Z0-9\-_.]+$')
    action: ServiceAction

    @validator('service_name')
    def validate_service_name(cls, v):
        if len(v) > 100:
            raise ValueError('Nom de service trop long')
        return v

class ServiceInfo(BaseModel):
    """Informations détaillées d'un service"""
    name: str
    status: ServiceStatus
    is_enabled: bool
    is_active: bool
    main_pid: Optional[int] = None
    memory_usage: Optional[int] = None
    cpu_usage: Optional[float] = None
    description: Optional[str] = None
    load_state: Optional[str] = None
    active_state: Optional[str] = None
    sub_state: Optional[str] = None

class ServiceActionResponse(BaseModel):
    """Réponse d'une action sur un service"""
    service: str
    action: ServiceAction
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    return_code: Optional[int] = None

class LogRequest(BaseModel):
    """Requête pour récupérer des logs"""
    service_name: str = Field(..., regex=r'^[a-zA-Z0-9\-_.]+$')
    lines: int = Field(default=50, ge=1, le=1000)
    follow: bool = False
    since: Optional[str] = None  # Format: "2023-01-01 12:00:00"

class LogEntry(BaseModel):
    """Entrée de log"""
    timestamp: str
    level: Optional[str] = None
    message: str
    service: str

class LogResponse(BaseModel):
    """Réponse avec logs"""
    service: str
    logs: List[LogEntry]
    total_lines: int
    truncated: bool = False