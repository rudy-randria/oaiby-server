from .system import router as system_router
from .hardware import router as hardware_router
from .network import router as network_router
from .services import router as services_router

__all__ = [
    "system_router",
    "hardware_router",
    "network_router", 
    "services_router"
]