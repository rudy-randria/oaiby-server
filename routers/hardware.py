from fastapi import APIRouter, HTTPException
from typing import List
from models.hardware import (
    CPUInfo, MemoryInfo, SwapInfo, DiskInfo, 
    DiskIOStats, TemperatureInfo
)
from services.hardware_service import HardwareService

router = APIRouter(
    prefix="/hardware",
    tags=["Hardware"],
    responses={404: {"description": "Not found"}}
)

@router.get("/cpu", response_model=CPUInfo)
async def get_cpu_info():
    """
    Récupère les informations détaillées du CPU
    
    - **count**: Nombre de cœurs physiques
    - **count_logical**: Nombre de cœurs logiques (avec hyperthreading)
    - **percent**: Utilisation CPU globale
    - **freq_current**: Fréquence actuelle en MHz
    - **freq_max**: Fréquence maximale en MHz
    - **temp**: Température en °C (si disponible)
    - **usage_per_core**: Utilisation par cœur
    """
    try:
        return HardwareService.get_cpu_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory", response_model=MemoryInfo)
async def get_memory_info():
    """
    Récupère les informations de la mémoire RAM
    
    - **total**: Mémoire totale en bytes
    - **available**: Mémoire disponible en bytes
    - **percent**: Pourcentage d'utilisation
    - **used**: Mémoire utilisée en bytes
    - **free**: Mémoire libre en bytes
    - **cached**: Mémoire en cache (si disponible)
    - **buffers**: Buffers système (si disponible)
    """
    try:
        return HardwareService.get_memory_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/swap", response_model=SwapInfo)
async def get_swap_info():
    """
    Récupère les informations de la mémoire swap
    
    - **total**: Swap total en bytes
    - **used**: Swap utilisé en bytes
    - **free**: Swap libre en bytes
    - **percent**: Pourcentage d'utilisation
    - **sin**: Pages swappées depuis le démarrage
    - **sout**: Pages dé-swappées depuis le démarrage
    """
    try:
        return HardwareService.get_swap_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/disks", response_model=List[DiskInfo])
async def get_disk_info():
    """
    Récupère les informations de tous les disques/partitions
    
    Pour chaque partition:
    - **mountpoint**: Point de montage
    - **device**: Périphérique (/dev/sda1, etc.)
    - **fstype**: Type de système de fichiers
    - **total**: Espace total en bytes
    - **used**: Espace utilisé en bytes
    - **free**: Espace libre en bytes
    - **percent**: Pourcentage d'utilisation
    """
    try:
        return HardwareService.get_disk_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/disks/io", response_model=List[DiskIOStats])
async def get_disk_io_stats():
    """
    Récupère les statistiques I/O des disques
    
    Pour chaque disque:
    - **device**: Nom du périphérique
    - **read_count**: Nombre de lectures
    - **write_count**: Nombre d'écritures
    - **read_bytes**: Bytes lus
    - **write_bytes**: Bytes écrits
    - **read_time**: Temps de lecture (ms)
    - **write_time**: Temps d'écriture (ms)
    """
    try:
        return HardwareService.get_disk_io_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/temperatures", response_model=List[TemperatureInfo])
async def get_temperature_info():
    """
    Récupère les informations de température de tous les capteurs
    
    Pour chaque capteur:
    - **label**: Nom du capteur
    - **current**: Température actuelle en °C
    - **high**: Seuil d'alerte (si disponible)
    - **critical**: Seuil critique (si disponible)
    """
    try:
        return HardwareService.get_temperature_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_hardware_summary():
    """
    Récupère un résumé complet du hardware
    
    Informations consolidées:
    - CPU: cœurs, utilisation, fréquence, température
    - Mémoire: total, utilisé, disponible
    - Swap: utilisation
    - Stockage: espace total/utilisé/libre
    - Thermal: température maximale
    """
    try:
        return HardwareService.get_hardware_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def check_hardware_health():
    """
    Vérifie la santé du hardware
    
    Retourne un rapport de santé avec:
    - **overall_status**: Statut global (OK, WARN, CRITICAL)
    - **issues**: Liste des problèmes critiques
    - **warnings**: Liste des avertissements
    - **recommendations**: Recommandations d'amélioration
    
    Critères vérifiés:
    - Utilisation CPU > 90% (critique) ou > 75% (warning)
    - Température CPU > 80°C (critique) ou > 70°C (warning)
    - Utilisation mémoire > 95% (critique) ou > 85% (warning)
    - Utilisation disque > 95% (critique) ou > 85% (warning)
    - Utilisation swap > 50% (warning)
    """
    try:
        return HardwareService.check_hardware_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/full")
async def get_full_hardware_info():
    """
    Récupère toutes les informations hardware en une seule requête
    
    Combine CPU, mémoire, swap, disques, températures et santé
    """
    try:
        cpu = HardwareService.get_cpu_info()
        memory = HardwareService.get_memory_info()
        swap = HardwareService.get_swap_info()
        disks = HardwareService.get_disk_info()
        disk_io = HardwareService.get_disk_io_stats()
        temperatures = HardwareService.get_temperature_info()
        health = HardwareService.check_hardware_health()
        summary = HardwareService.get_hardware_summary()
        
        return {
            "cpu": cpu,
            "memory": memory,
            "swap": swap,
            "disks": disks,
            "disk_io": disk_io,
            "temperatures": temperatures,
            "health": health,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))