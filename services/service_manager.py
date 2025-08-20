import subprocess
import re
import json
from typing import List, Dict, Optional
from datetime import datetime
from models.services import (
    ServiceAction, ServiceStatus, ServiceInfo, 
    ServiceActionResponse, LogEntry, LogResponse
)

class ServiceManager:
    """Service pour gérer les services systemd"""
    
    @staticmethod
    def execute_service_action(service_name: str, action: ServiceAction) -> ServiceActionResponse:
        """Exécute une action sur un service"""
        try:
            # Valider le nom du service
            if not ServiceManager._is_valid_service_name(service_name):
                raise Exception(f"Nom de service invalide: {service_name}")
            
            # Construire la commande
            cmd = f"systemctl {action.value} {service_name}"
            
            # Exécuter la commande
            result = subprocess.run(
                cmd, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            return ServiceActionResponse(
                service=service_name,
                action=action,
                success=result.returncode == 0,
                output=result.stdout.strip() if result.stdout else None,
                error=result.stderr.strip() if result.stderr else None,
                return_code=result.returncode
            )
        except subprocess.TimeoutExpired:
            raise Exception(f"Timeout lors de l'exécution de l'action {action.value} sur {service_name}")
        except Exception as e:
            raise Exception(f"Erreur action service: {str(e)}")
    
    @staticmethod
    def get_service_status(service_name: str) -> ServiceInfo:
        """Récupère les informations détaillées d'un service"""
        try:
            if not ServiceManager._is_valid_service_name(service_name):
                raise Exception(f"Nom de service invalide: {service_name}")
            
            # Récupérer les informations avec systemctl show
            cmd = f"systemctl show {service_name} --no-page"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                raise Exception(f"Service {service_name} introuvable")
            
            # Parser les informations
            info = {}
            for line in result.stdout.strip().split('\n'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    info[key] = value
            
            # Déterminer le statut
            active_state = info.get('ActiveState', 'unknown')
            status_map = {
                'active': ServiceStatus.ACTIVE,
                'inactive': ServiceStatus.INACTIVE,
                'failed': ServiceStatus.FAILED,
                'activating': ServiceStatus.ACTIVATING,
                'deactivating': ServiceStatus.DEACTIVATING
            }
            status = status_map.get(active_state, ServiceStatus.UNKNOWN)
            
            # Récupérer les métriques de performance si le service est actif
            memory_usage = None
            cpu_usage = None
            main_pid = None
            
            if status == ServiceStatus.ACTIVE:
                main_pid_str = info.get('MainPID', '0')
                if main_pid_str.isdigit() and int(main_pid_str) > 0:
                    main_pid = int(main_pid_str)
                    try:
                        import psutil
                        proc = psutil.Process(main_pid)
                        memory_usage = proc.memory_info().rss
                        cpu_usage = proc.cpu_percent()
                    except:
                        pass
            
            return ServiceInfo(
                name=service_name,
                status=status,
                is_enabled=info.get('UnitFileState', 'disabled') == 'enabled',
                is_active=active_state == 'active',
                main_pid=main_pid,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                description=info.get('Description', ''),
                load_state=info.get('LoadState', ''),
                active_state=active_state,
                sub_state=info.get('SubState', '')
            )
        except Exception as e:
            raise Exception(f"Erreur récupération statut service: {str(e)}")
    
    @staticmethod
    def get_service_logs(service_name: str, lines: int = 50, since: Optional[str] = None) -> LogResponse:
        """Récupère les logs d'un service"""
        try:
            if not ServiceManager._is_valid_service_name(service_name):
                raise Exception(f"Nom de service invalide: {service_name}")
            
            # Construire la commande journalctl
            cmd = f"journalctl -u {service_name} -n {lines} --no-pager --output=json"
            
            if since:
                cmd += f" --since='{since}'"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"Erreur récupération logs: {result.stderr}")
            
            # Parser les logs JSON
            log_entries = []
            lines_output = result.stdout.strip().split('\n')
            
            for line in lines_output:
                if line.strip():
                    try:
                        log_data = json.loads(line)
                        timestamp = log_data.get('__REALTIME_TIMESTAMP', '')
                        if timestamp:
                            # Convertir microseconds timestamp en datetime
                            dt = datetime.fromtimestamp(int(timestamp) / 1000000)
                            timestamp_str = dt.isoformat()
                        else:
                            timestamp_str = datetime.now().isoformat()
                        
                        log_entries.append(LogEntry(
                            timestamp=timestamp_str,
                            level=log_data.get('PRIORITY', '6'),  # 6 = info par défaut
                            message=log_data.get('MESSAGE', ''),
                            service=service_name
                        ))
                    except json.JSONDecodeError:
                        # Si le parsing JSON échoue, traiter comme texte simple
                        log_entries.append(LogEntry(
                            timestamp=datetime.now().isoformat(),
                            level=None,
                            message=line,
                            service=service_name
                        ))
            
            return LogResponse(
                service=service_name,
                logs=log_entries,
                total_lines=len(log_entries),
                truncated=len(log_entries) >= lines
            )
        except Exception as e:
            raise Exception(f"Erreur récupération logs: {str(e)}")
    
    @staticmethod
    def list_services(status_filter: Optional[str] = None) -> List[ServiceInfo]:
        """Liste tous les services avec filtrage optionnel"""
        try:
            cmd = "systemctl list-units --type=service --no-page --plain"
            if status_filter:
                cmd += f" --state={status_filter}"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise Exception(f"Erreur listage services: {result.stderr}")
            
            services = []
            for line in result.stdout.strip().split('\n'):
                if line.strip() and not line.startswith('UNIT'):
                    # Parser la ligne de sortie systemctl
                    parts = line.split()
                    if len(parts) >= 4:
                        service_name = parts[0].replace('.service', '')
                        try:
                            service_info = ServiceManager.get_service_status(service_name)
                            services.append(service_info)
                        except:
                            # Ignorer les services qui ne peuvent pas être interrogés
                            continue
            
            return services
        except Exception as e:
            raise Exception(f"Erreur liste services: {str(e)}")
    
    @staticmethod
    def get_failed_services() -> List[ServiceInfo]:
        """Récupère la liste des services en échec"""
        try:
            return ServiceManager.list_services("failed")
        except Exception as e:
            raise Exception(f"Erreur récupération services échoués: {str(e)}")
    
    @staticmethod
    def get_service_dependencies(service_name: str) -> Dict[str, List[str]]:
        """Récupère les dépendances d'un service"""
        try:
            if not ServiceManager._is_valid_service_name(service_name):
                raise Exception(f"Nom de service invalide: {service_name}")
            
            dependencies = {
                "requires": [],
                "wants": [],
                "required_by": [],
                "wanted_by": []
            }
            
            # Récupérer les dépendances
            for dep_type in ["Requires", "Wants", "RequiredBy", "WantedBy"]:
                cmd = f"systemctl show {service_name} --property={dep_type} --value"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip():
                    deps = [dep.strip() for dep in result.stdout.strip().split() if dep.strip()]
                    dependencies[dep_type.lower().replace("by", "_by")] = deps
            
            return dependencies
        except Exception as e:
            raise Exception(f"Erreur récupération dépendances: {str(e)}")
    
    @staticmethod
    def restart_service_with_dependencies(service_name: str) -> Dict[str, ServiceActionResponse]:
        """Redémarre un service et ses dépendances"""
        try:
            if not ServiceManager._is_valid_service_name(service_name):
                raise Exception(f"Nom de service invalide: {service_name}")
            
            results = {}
            
            # Récupérer les dépendances
            deps = ServiceManager.get_service_dependencies(service_name)
            
            # Arrêter le service principal d'abord
            results[service_name] = ServiceManager.execute_service_action(
                service_name, ServiceAction.STOP
            )
            
            # Arrêter les services dépendants
            for dep_service in deps.get("wanted_by", []):
                dep_name = dep_service.replace(".service", "")
                try:
                    results[dep_name] = ServiceManager.execute_service_action(
                        dep_name, ServiceAction.STOP
                    )
                except:
                    continue
            
            # Redémarrer dans l'ordre inverse
            for dep_service in reversed(deps.get("wanted_by", [])):
                dep_name = dep_service.replace(".service", "")
                try:
                    results[f"{dep_name}_start"] = ServiceManager.execute_service_action(
                        dep_name, ServiceAction.START
                    )
                except:
                    continue
            
            # Redémarrer le service principal
            results[f"{service_name}_start"] = ServiceManager.execute_service_action(
                service_name, ServiceAction.START
            )
            
            return results
        except Exception as e:
            raise Exception(f"Erreur redémarrage avec dépendances: {str(e)}")
    
    @staticmethod
    def get_service_metrics(service_name: str) -> Dict:
        """Récupère les métriques de performance d'un service"""
        try:
            if not ServiceManager._is_valid_service_name(service_name):
                raise Exception(f"Nom de service invalide: {service_name}")
            
            service_info = ServiceManager.get_service_status(service_name)
            
            metrics = {
                "service": service_name,
                "status": service_info.status.value,
                "uptime": None,
                "memory_usage": service_info.memory_usage,
                "cpu_usage": service_info.cpu_usage,
                "restart_count": 0,
                "last_restart": None
            }
            
            # Récupérer les métriques supplémentaires avec systemctl show
            cmd = f"systemctl show {service_name} --property=ActiveEnterTimestamp,NRestarts"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if key == "ActiveEnterTimestamp" and value:
                            try:
                                # Parser timestamp systemd
                                import dateutil.parser
                                start_time = dateutil.parser.parse(value)
                                uptime = (datetime.now(start_time.tzinfo) - start_time).total_seconds()
                                metrics["uptime"] = uptime
                            except:
                                pass
                        elif key == "NRestarts":
                            try:
                                metrics["restart_count"] = int(value)
                            except:
                                pass
            
            return metrics
        except Exception as e:
            raise Exception(f"Erreur récupération métriques service: {str(e)}")
    
    @staticmethod
    def _is_valid_service_name(service_name: str) -> bool:
        """Valide le nom d'un service"""
        # Vérifier le format du nom de service
        if not re.match(r'^[a-zA-Z0-9\-_.@]+, service_name):
            return False
        
        # Vérifier la longueur
        if len(service_name) > 100:
            return False
        
        # Services interdits pour des raisons de sécurité
        forbidden_services = [
            'init', 'kernel', 'kthread', 'migration', 'rcu_',
            'watchdog', 'systemd', 'dbus'
        ]
        
        for forbidden in forbidden_services:
            if service_name.startswith(forbidden):
                return False
        
        return True
    
    @staticmethod
    def backup_service_config(service_name: str) -> Dict:
        """Sauvegarde la configuration d'un service"""
        try:
            if not ServiceManager._is_valid_service_name(service_name):
                raise Exception(f"Nom de service invalide: {service_name}")
            
            # Récupérer le chemin du fichier de service
            cmd = f"systemctl show {service_name} --property=FragmentPath --value"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0 or not result.stdout.strip():
                raise Exception(f"Impossible de trouver le fichier de configuration pour {service_name}")
            
            config_path = result.stdout.strip()
            
            # Lire le contenu du fichier
            try:
                with open(config_path, 'r') as f:
                    config_content = f.read()
            except PermissionError:
                raise Exception(f"Permission refusée pour lire {config_path}")
            except FileNotFoundError:
                raise Exception(f"Fichier de configuration introuvable: {config_path}")
            
            return {
                "service": service_name,
                "config_path": config_path,
                "config_content": config_content,
                "backup_timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise Exception(f"Erreur sauvegarde config service: {str(e)}")
    
    @staticmethod
    def get_system_services_overview() -> Dict:
        """Récupère un aperçu de tous les services système"""
        try:
            overview = {
                "total_services": 0,
                "active_services": 0,
                "failed_services": 0,
                "inactive_services": 0,
                "enabled_services": 0,
                "disabled_services": 0,
                "services_by_status": {},
                "high_memory_services": [],
                "high_cpu_services": []
            }
            
            # Compter tous les services
            cmd = "systemctl list-unit-files --type=service --no-page --plain"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                overview["total_services"] = len([line for line in lines if '.service' in line])
            
            # Récupérer les services actifs
            active_services = ServiceManager.list_services("active")
            overview["active_services"] = len(active_services)
            
            # Récupérer les services échoués
            failed_services = ServiceManager.list_services("failed")
            overview["failed_services"] = len(failed_services)
            
            # Calculer les autres statistiques
            overview["inactive_services"] = overview["total_services"] - overview["active_services"] - overview["failed_services"]
            
            # Services avec haute consommation
            for service in active_services:
                if service.memory_usage and service.memory_usage > 100 * 1024 * 1024:  # > 100MB
                    overview["high_memory_services"].append({
                        "name": service.name,
                        "memory_mb": round(service.memory_usage / (1024 * 1024), 2)
                    })
                
                if service.cpu_usage and service.cpu_usage > 5.0:  # > 5% CPU
                    overview["high_cpu_services"].append({
                        "name": service.name,
                        "cpu_percent": service.cpu_usage
                    })
            
            # Trier par consommation
            overview["high_memory_services"].sort(key=lambda x: x["memory_mb"], reverse=True)
            overview["high_cpu_services"].sort(key=lambda x: x["cpu_percent"], reverse=True)
            
            return overview
        except Exception as e:
            raise Exception(f"Erreur aperçu services système: {str(e)}")