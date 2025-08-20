from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
from models.system import SystemInfo, SystemLoad, ProcessInfo, SystemAction
from services.system_service import SystemService

router = APIRouter(
    prefix="/system",
    tags=["System"],
    responses={404: {"description": "Not found"}}
)

@router.get("/info", response_model=SystemInfo)
async def get_system_info():
    """
    Récupère les informations générales du système
    
    - **hostname**: Nom de la machine
    - **os**: Système d'exploitation et version
    - **architecture**: Architecture du processeur
    - **boot_time**: Heure de démarrage
    - **uptime**: Temps de fonctionnement en secondes
    """
    try:
        return SystemService.get_system_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/load", response_model=SystemLoad)
async def get_system_load():
    """
    Récupère la charge système (load average)
    
    - **load_1min**: Charge moyenne sur 1 minute
    - **load_5min**: Charge moyenne sur 5 minutes  
    - **load_15min**: Charge moyenne sur 15 minutes
    - **cpu_count**: Nombre de cœurs CPU
    """
    try:
        return SystemService.get_system_load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processes", response_model=List[ProcessInfo])
async def get_processes(
    limit: int = Query(default=10, ge=1, le=100, description="Nombre de processus à retourner"),
    sort_by: str = Query(default="cpu", regex="^(cpu|memory|name)$", description="Critère de tri")
):
    """
    Récupère la liste des processus en cours
    
    - **limit**: Nombre maximum de processus (1-100)
    - **sort_by**: Critère de tri (cpu, memory, name)
    """
    try:
        return SystemService.get_processes(limit=limit, sort_by=sort_by)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/processes/{pid}")
async def kill_process(
    pid: int = Path(..., gt=0, description="ID du processus à terminer"),
    signal: int = Query(default=15, ge=1, le=31, description="Signal à envoyer (15=TERM, 9=KILL)")
):
    """
    Termine un processus par son PID
    
    - **pid**: ID du processus (doit être > 0)
    - **signal**: Signal à envoyer (15=SIGTERM, 9=SIGKILL)
    
    ⚠️ **Attention**: Cette action est irréversible !
    """
    try:
        # Vérifications de sécurité
        if pid in [0, 1]:  # Protéger init et kernel
            raise HTTPException(status_code=403, detail="Impossible de terminer ce processus système")
        
        result = SystemService.kill_process(pid, signal)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/action")
async def execute_system_action(action: SystemAction):
    """
    Exécute une action système (reboot, shutdown)
    
    - **action**: Action à effectuer (reboot, shutdown, halt)
    - **delay**: Délai en secondes (optionnel)
    - **message**: Message à afficher (optionnel)
    
    ⚠️ **DANGER**: Cette action peut redémarrer/arrêter le serveur !
    """
    try:
        result = SystemService.execute_system_action(action)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/uptime")
async def get_uptime():
    """
    Récupère le temps de fonctionnement formaté
    """
    try:
        uptime_formatted = SystemService.get_uptime_formatted()
        load = SystemService.get_system_load()
        
        return {
            "uptime_formatted": uptime_formatted,
            "uptime_seconds": load.load_1min,  # Utiliser la charge comme proxy
            "boot_time": SystemService.get_system_info().boot_time
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users")
async def get_system_users():
    """
    Récupère la liste des utilisateurs connectés
    """
    try:
        return {"users": SystemService.get_system_users()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def check_system_health():
    """
    Vérifie la santé générale du système
    
    Retourne un rapport de santé avec:
    - Statut global (OK, WARN, CRITICAL)
    - État du CPU, mémoire, disque, charge
    - Recommandations d'amélioration
    """
    try:
        return SystemService.check_system_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_system_summary():
    """
    Récupère un résumé complet du système
    """
    try:
        info = SystemService.get_system_info()
        load = SystemService.get_system_load()
        health = SystemService.check_system_health()
        users = SystemService.get_system_users()
        
        return {
            "info": info,
            "load": load,
            "health": health,
            "connected_users": len(users),
            "uptime_formatted": SystemService.get_uptime_formatted()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))