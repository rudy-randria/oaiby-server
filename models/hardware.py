from pydantic import BaseModel
from typing import Optional, List

class CPUInfo(BaseModel):
    """Informations CPU"""
    count: int
    count_logical: int
    percent: float
    freq_current: Optional[float] = None
    freq_max: Optional[float] = None
    freq_min: Optional[float] = None
    temp: Optional[float] = None
    usage_per_core: Optional[List[float]] = None

class MemoryInfo(BaseModel):
    """Informations mémoire RAM"""
    total: int
    available: int
    percent: float
    used: int
    free: int
    cached: Optional[int] = None
    buffers: Optional[int] = None

class SwapInfo(BaseModel):
    """Informations swap"""
    total: int
    used: int
    free: int
    percent: float
    sin: int  # swap in
    sout: int  # swap out

class DiskInfo(BaseModel):
    """Informations disque"""
    mountpoint: str
    device: str
    fstype: str
    total: int
    used: int
    free: int
    percent: float

class DiskIOStats(BaseModel):
    """Statistiques I/O disque"""
    device: str
    read_count: int
    write_count: int
    read_bytes: int
    write_bytes: int
    read_time: int
    write_time: int

class TemperatureInfo(BaseModel):
    """Informations température"""
    label: str
    current: float
    high: Optional[float] = None
    critical: Optional[float] = None