"""Modèles Pydantic pour l'API VPS Manager"""

# Imports des modèles d'authentification
from .auth import (
    LoginRequest,
    LoginResponse,
    UserInfo,
    TokenData,
    LogoutResponse,
    ErrorResponse,
    CreateUserRequest,
    UpdateUserRequest,
    ChangePasswordRequest
)

# Imports des modèles système
from .system import (
    SystemInfo,
    SystemLoad,
    ProcessInfo,
    SystemAction
)

# Imports des modèles hardware
from .hardware import (
    CPUInfo,
    MemoryInfo,
    SwapInfo,
    DiskInfo,
    DiskIOStats,
    TemperatureInfo
)

# Imports des modèles réseau
from .network import (
    NetworkInterface,
    NetworkIOStats,
    NetworkConnection,
    NetworkSummary
)

# Imports des modèles services
from .services import (
    ServiceAction,
    ServiceStatus,
    ServiceManageRequest,
    ServiceInfo,
    ServiceActionResponse,
    LogRequest,
    LogEntry,
    LogResponse
)

# Export de tous les modèles
__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "UserInfo",
    "TokenData",
    "LogoutResponse",
    "ErrorResponse",
    "CreateUserRequest",
    "UpdateUserRequest",
    "ChangePasswordRequest",
    # System
    "SystemInfo",
    "SystemLoad", 
    "ProcessInfo",
    "SystemAction",
    # Hardware
    "CPUInfo",
    "MemoryInfo",
    "SwapInfo",
    "DiskInfo",
    "DiskIOStats",
    "TemperatureInfo",
    # Network
    "NetworkInterface",
    "NetworkIOStats",
    "NetworkConnection",
    "NetworkSummary",
    # Services
    "ServiceAction",
    "ServiceStatus",
    "ServiceManageRequest",
    "ServiceInfo",
    "ServiceActionResponse",
    "LogRequest",
    "LogEntry",
    "LogResponse"
]