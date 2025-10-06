"""Routers pour l'API VPS Manager"""

from .auth import router as auth_router
from .system import router as system_router
from .hardware import router as hardware_router
from .network import router as network_router
from .services import router as services_router
from .face_recognition import router as face_recognition_router
__all__ = [
    "auth_router",
    "system_router",
    "hardware_router",
    "network_router", 
    "services_router",
    "face_recognition_router"
]