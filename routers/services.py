from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Optional
from models.services import (
    ServiceAction, ServiceManageRequest, ServiceInfo, 
    ServiceActionResponse, LogRequest, LogResponse
)
from services.service_manager import ServiceManager

router = APIRouter(
    prefix="/services",
    tags=["Services"],
    responses={404: {"description": "Not found"}}
)

@router.post("/manage", response_model=ServiceActionResponse)
async def manage_service(request: ServiceManageRequest):
    """
    Exécute une action sur un service systemd
    
    - **service_name**: Nom du service (nginx, mysql, etc.)
    - **action**: Action à effectuer (start, stop, restart, enable, disable)
    
    ⚠️ **Attention**: Cette action peut affecter le fonctionnement du serveur !
    
    **Exemples**:
    ```json
    {
        "service_name": "nginx",
        "action": "restart"
    }
    ```
    """
    try:
        return ServiceManager.execute_service_action(
            request.service_name, 
            request.action
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{service_name}", response_model=ServiceInfo)
async def get_service_status(
    service_name: str = Path(..., regex=r'^[a-zA-Z0-9\-_.]+$', description="Nom du service")
):
    """
    Récupère le statut détaillé d'un service
    
    - **name**: Nom du service
    - **status**: État (active, inactive, failed, etc.)
    - **is_enabled**: Service activé au démarrage
    - **is_active**: Service actuellement actif
    - **main_pid**: PID du processus principal
    - **memory_usage**: Utilisation mémoire en bytes
    - **cpu_usage**: Utilisation CPU en pourcentage
    - **description**: Description du service
    """
    try:
        return ServiceManager.get_service_status(service_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/{service_name}", response_model=LogResponse)
async def get_service_logs(
    service_name: str = Path(..., regex=r'^[a-zA-Z0-9\-_.]+$'),
    lines: int = Query(default=50, ge=1, le=1000, description="Nombre de lignes"),
    since: Optional[str] = Query(default=None, description="Depuis quand (2023-01-01 12:00:00)")
):
    """
    Récupère les logs d'un service
    
    - **lines**: Nombre de lignes à récupérer (1-1000)
    - **since**: Filtrer depuis une date (format: YYYY-MM-DD HH:MM:SS)
    
    **Exemple**: `/services/logs/nginx?lines=100&since=2024-01-01 10:00:00`
    """
    try:
        return ServiceManager.get_service_logs(
            service_name=service_name,
            lines=lines,
            since=since
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list", response_model=List[ServiceInfo])
async def list_services(
    status_filter: Optional[str] = Query(
        default=None, 
        regex="^(active|inactive|failed|activating|deactivating)$",
        description="Filtrer par statut"
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Nombre maximum de services")
):
    """
    Liste tous les services avec filtrage optionnel
    
    - **status_filter**: Filtrer par statut (active, inactive, failed, etc.)
    - **limit**: Nombre maximum de services à retourner
    
    **Exemples**:
    - `/services/list` - Tous les services
    - `/services/list?status_filter=active` - Services actifs seulement
    - `/services/list?status_filter=failed` - Services en échec
    """
    try:
        services = ServiceManager.list_services(status_filter)
        return services[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/failed", response_model=List[ServiceInfo])
async def get_failed_services():
    """
    Récupère la liste des services en échec
    
    Utile pour identifier rapidement les problèmes système
    """
    try:
        return ServiceManager.get_failed_services()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dependencies/{service_name}")
async def get_service_dependencies(
    service_name: str = Path(..., regex=r'^[a-zA-Z0-9\-_.]+$')
):
    """
    Récupère les dépendances d'un service
    
    - **requires**: Services requis pour fonctionner
    - **wants**: Services souhaités (optionnels)
    - **required_by**: Services qui nécessitent ce service
    - **wanted_by**: Services qui souhaitent ce service
    """
    try:
        return ServiceManager.get_service_dependencies(service_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restart-with-deps/{service_name}")
async def restart_service_with_dependencies(
    service_name: str = Path(..., regex=r'^[a-zA-Z0-9\-_.]+$')
):
    """
    Redémarre un service et ses dépendances
    
    ⚠️ **ATTENTION**: Cette action peut affecter plusieurs services !
    
    Séquence:
    1. Arrêt du service principal
    2. Arrêt des services dépendants
    3. Redémarrage des dépendances
    4. Redémarrage du service principal
    """
    try:
        return ServiceManager.restart_service_with_dependencies(service_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics/{service_name}")
async def get_service_metrics(
    service_name: str = Path(..., regex=r'^[a-zA-Z0-9\-_.]+$')
):
    """
    Récupère les métriques de performance d'un service
    
    - **uptime**: Temps de fonctionnement en secondes
    - **memory_usage**: Utilisation mémoire
    - **cpu_usage**: Utilisation CPU
    - **restart_count**: Nombre de redémarrages
    - **last_restart**: Dernière heure de redémarrage
    """
    try:
        return ServiceManager.get_service_metrics(service_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/backup-config/{service_name}")
async def backup_service_config(
    service_name: str = Path(..., regex=r'^[a-zA-Z0-9\-_.]+$')
):
    """
    Sauvegarde la configuration d'un service
    
    Retourne le contenu du fichier de configuration systemd
    Utile avant de faire des modifications
    """
    try:
        return ServiceManager.backup_service_config(service_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/overview")
async def get_services_overview():
    """
    Récupère un aperçu général de tous les services
    
    Statistiques globales:
    - Nombre total de services
    - Services actifs/inactifs/échoués
    - Services activés/désactivés
    - Services consommant beaucoup de ressources
    
    Utile pour le monitoring global du système
    """
    try:
        return ServiceManager.get_system_services_overview()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_services(
    query: str = Query(..., min_length=2, max_length=50, description="Terme de recherche"),
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Recherche des services par nom ou description
    
    - **query**: Terme à rechercher (minimum 2 caractères)
    - **limit**: Nombre maximum de résultats
    """
    try:
        all_services = ServiceManager.list_services()
        
        # Filtrer les services qui correspondent à la requête
        matching_services = []
        query_lower = query.lower()
        
        for service in all_services:
            if (query_lower in service.name.lower() or 
                (service.description and query_lower in service.description.lower())):
                matching_services.append(service)
        
        return {
            "query": query,
            "results": matching_services[:limit],
            "total_found": len(matching_services)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk-action")
async def bulk_service_action(
    services: List[str] = Query(..., description="Liste des noms de services"),
    action: ServiceAction = Query(..., description="Action à effectuer"),
    continue_on_error: bool = Query(default=True, description="Continuer en cas d'erreur")
):
    """
    Exécute une action sur plusieurs services en une fois
    
    - **services**: Liste des noms de services
    - **action**: Action à effectuer sur tous les services
    - **continue_on_error**: Continuer même si une action échoue
    
    ⚠️ **DANGER**: Cette action peut affecter plusieurs services critiques !
    
    **Exemple**:
    ```
    POST /services/bulk-action?action=restart&continue_on_error=true
    services=["nginx", "mysql", "redis"]
    ```
    """
    try:
        results = {}
        errors = []
        
        for service_name in services:
            try:
                # Valider le nom du service
                if not service_name or len(service_name) > 100:
                    errors.append(f"Nom de service invalide: {service_name}")
                    if not continue_on_error:
                        break
                    continue
                
                result = ServiceManager.execute_service_action(service_name, action)
                results[service_name] = result
                
            except Exception as e:
                error_msg = f"Erreur pour {service_name}: {str(e)}"
                errors.append(error_msg)
                
                if not continue_on_error:
                    break
        
        return {
            "action": action.value,
            "services_count": len(services),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def check_services_health():
    """
    Vérifie la santé générale des services
    
    Analyse:
    - Services critiques en échec
    - Services utilisant trop de ressources
    - Services redémarrés fréquemment
    - Recommandations d'optimisation
    """
    try:
        failed_services = ServiceManager.get_failed_services()
        overview = ServiceManager.get_system_services_overview()
        
        health_report = {
            "overall_status": "OK",
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Vérifier les services échoués
        if len(failed_services) > 0:
            health_report["issues"].extend([
                f"Service en échec: {service.name}" for service in failed_services
            ])
            health_report["overall_status"] = "CRITICAL"
        
        # Vérifier la consommation mémoire
        high_memory = overview.get("high_memory_services", [])
        if len(high_memory) > 3:
            health_report["warnings"].append(
                f"{len(high_memory)} services consomment beaucoup de mémoire"
            )
            if health_report["overall_status"] == "OK":
                health_report["overall_status"] = "WARN"
        
        # Vérifier la consommation CPU
        high_cpu = overview.get("high_cpu_services", [])
        if len(high_cpu) > 2:
            health_report["warnings"].append(
                f"{len(high_cpu)} services consomment beaucoup de CPU"
            )
            if health_report["overall_status"] == "OK":
                health_report["overall_status"] = "WARN"
        
        # Recommandations
        if len(high_memory) > 0:
            health_report["recommendations"].append(
                "Optimiser la consommation mémoire des services gourmands"
            )
        
        if len(failed_services) > 0:
            health_report["recommendations"].append(
                "Vérifier les logs des services en échec"
            )
        
        return {
            **health_report,
            "failed_services": [s.name for s in failed_services],
            "high_memory_services": [s["name"] for s in high_memory[:5]],
            "high_cpu_services": [s["name"] for s in high_cpu[:5]]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))