from pydantic import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # API
    API_TITLE: str = "VPS Resource Manager API"
    API_VERSION: str = "2.0.0"
    API_DESCRIPTION: str = "API pour gérer les ressources d'un VPS Ubuntu"
    
    # Serveur
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    RELOAD: bool = False
    WORKERS: int = 1
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    ALLOWED_METHODS: List[str] = ["*"]
    ALLOWED_HEADERS: List[str] = ["*"]
    
    # Sécurité
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_COMMANDS: List[str] = [
        "systemctl", "service", "ps", "top", "htop", 
        "df", "free", "lscpu", "lsblk", "ip", "ss", "ping"
    ]
    
    # Monitoring
    MAX_PROCESSES_RETURN: int = 100
    MAX_LOG_LINES: int = 1000
    DEFAULT_LOG_LINES: int = 50
    HEALTH_CHECK_TIMEOUT: int = 30
    
    # Seuils d'alerte
    CPU_WARNING_THRESHOLD: float = 75.0
    CPU_CRITICAL_THRESHOLD: float = 90.0
    MEMORY_WARNING_THRESHOLD: float = 85.0
    MEMORY_CRITICAL_THRESHOLD: float = 95.0
    DISK_WARNING_THRESHOLD: float = 85.0
    DISK_CRITICAL_THRESHOLD: float = 95.0
    TEMPERATURE_WARNING_THRESHOLD: float = 70.0
    TEMPERATURE_CRITICAL_THRESHOLD: float = 80.0
    
    # Services système critiques (ne pas arrêter)
    CRITICAL_SERVICES: List[str] = [
        "systemd", "init", "kernel", "kthread", "migration",
        "rcu_", "watchdog", "dbus"
    ]
    
    # Chemins système
    SYSTEMD_PATH: str = "/etc/systemd/system"
    LOG_PATH: str = "/var/log"
    PROC_PATH: str = "/proc"
    SYS_PATH: str = "/sys"
    
    # Cache
    CACHE_TTL: int = 60  # secondes
    ENABLE_CACHE: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Instance globale des paramètres
settings = Settings()

# Configuration de logging
import logging

def setup_logging():
    """Configure le système de logging"""
    
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format=settings.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            *([logging.FileHandler(settings.LOG_FILE)] if settings.LOG_FILE else [])
        ]
    )
    
    # Logger pour l'application
    logger = logging.getLogger("vps_manager")
    
    return logger

# Configuration des tags pour FastAPI
TAGS_METADATA = [
    {
        "name": "System",
        "description": "Informations et actions système (processus, uptime, reboot)",
    },
    {
        "name": "Hardware", 
        "description": "Monitoring hardware (CPU, RAM, disques, températures)",
    },
    {
        "name": "Network",
        "description": "Informations réseau (interfaces, connexions, statistiques)",
    },
    {
        "name": "Services",
        "description": "Gestion des services systemd (start, stop, logs, status)",
    }
]

# Configuration OpenAPI
OPENAPI_CONFIG = {
    "title": settings.API_TITLE,
    "description": settings.API_DESCRIPTION,
    "version": settings.API_VERSION,
    "openapi_tags": TAGS_METADATA,
    "contact": {
        "name": "VPS Resource Manager",
        "email": "admin@example.com",
        "url": "https://github.com/your-repo/vps-manager"
    },
    "license_info": {
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
}