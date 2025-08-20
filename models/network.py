from pydantic import BaseModel
from typing import List, Optional
import ipaddress

class NetworkInterface(BaseModel):
    """Interface réseau"""
    name: str
    addresses: List[str]
    is_up: bool
    speed: Optional[int] = None  # Mbps
    mtu: Optional[int] = None

class NetworkIOStats(BaseModel):
    """Statistiques I/O réseau"""
    interface: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errin: int
    errout: int
    dropin: int
    dropout: int

class NetworkConnection(BaseModel):
    """Connexion réseau active"""
    fd: int
    family: str  # AF_INET, AF_INET6
    type: str    # SOCK_STREAM, SOCK_DGRAM
    local_address: str
    local_port: int
    remote_address: Optional[str] = None
    remote_port: Optional[int] = None
    status: str
    pid: Optional[int] = None

class NetworkSummary(BaseModel):
    """Résumé réseau"""
    interfaces: List[NetworkInterface]
    io_stats: List[NetworkIOStats]
    active_connections: int
    listening_ports: List[int]