import os
import psutil
import subprocess
from datetime import datetime
from typing import List, Optional
from models.system import SystemInfo, SystemLoad, ProcessInfo, SystemAction

class SystemService:
    """Service pour gérer les informations et actions système"""
    
    @staticmethod
    def get_system_info() -> SystemInfo:
        """Récupère les informations générales du système"""
        try:
            uname = os.uname()
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now().timestamp() - psutil.boot_time()
            
            return SystemInfo(
                hostname=uname.nodename,
                os=f"{uname.sysname} {uname.release}",
                architecture=uname.machine,
                boot_time=boot_time,
                uptime=uptime
            )
        except Exception as e:
            raise Exception(f"Erreur récupération info système: {str(e)}")
    
    @staticmethod
    def get_system_load() -> SystemLoad:
        """Récupère la charge système"""
        try:
            load1, load5, load15 = os.getloadavg()
            return SystemLoad(
                load_1min=load1,
                load_5min=load5,
                load_15min=load15,
                cpu_count=psutil.cpu_count()
            )
        except Exception as e:
            raise Exception(f"Erreur récupération charge système: {str(e)}")
    
    @staticmethod
    def get_processes(limit: int = 10, sort_by: str = "cpu") -> List[ProcessInfo]:
        """Récupère la liste des processus"""
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                           'status', 'create_time', 'username', 'cmdline']):
                try:
                    pinfo = proc.info
                    processes.append(ProcessInfo(
                        pid=pinfo['pid'],
                        name=pinfo['name'] or 'Unknown',
                        cpu_percent=pinfo['cpu_percent'] or 0,
                        memory_percent=pinfo['memory_percent'] or 0,
                        status=pinfo['status'],
                        create_time=datetime.fromtimestamp(pinfo['create_time']),
                        user=pinfo.get('username'),
                        cmdline=pinfo.get('cmdline', [])
                    ))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # Trier selon le critère demandé
            if sort_by == "cpu":
                processes.sort(key=lambda x: x.cpu_percent, reverse=True)
            elif sort_by == "memory":
                processes.sort(key=lambda x: x.memory_percent, reverse=True)
            elif sort_by == "name":
                processes.sort(key=lambda x: x.name.lower())
            
            return processes[:limit]
        except Exception as e:
            raise Exception(f"Erreur récupération processus: {str(e)}")
    
    @staticmethod
    def kill_process(pid: int, signal: int = 15) -> dict:
        """Termine un processus"""
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
            
            if signal == 9:  # SIGKILL
                proc.kill()
            else:  # SIGTERM par défaut
                proc.terminate()
            
            return {
                "success": True,
                "message": f"Processus {proc_name} (PID: {pid}) terminé",
                "signal": signal
            }
        except psutil.NoSuchProcess:
            raise Exception(f"Processus avec PID {pid} introuvable")
        except psutil.AccessDenied:
            raise Exception(f"Permission refusée pour terminer le processus {pid}")
        except Exception as e:
            raise Exception(f"Erreur lors de l'arrêt du processus: {str(e)}")
    
    @staticmethod
    def execute_system_action(action: SystemAction) -> dict:
        """Exécute une action système (reboot, shutdown)"""
        try:
            allowed_actions = ["reboot", "shutdown", "halt"]
            if action.action not in allowed_actions:
                raise Exception(f"Action non autorisée: {action.action}")
            
            cmd_map = {
                "reboot": "sudo reboot",
                "shutdown": f"sudo shutdown -h {action.delay or 0}",
                "halt": "sudo halt"
            }
            
            command = cmd_map[action.action]
            if action.delay and action.action == "shutdown":
                command = f"sudo shutdown -h +{action.delay}"
            
            if action.message:
                command += f' "{action.message}"'
            
            # Exécuter la commande en arrière-plan
            subprocess.Popen(command, shell=True)
            
            return {
                "success": True,
                "action": action.action,
                "delay": action.delay,
                "message": f"Action {action.action} programmée"
            }
        except Exception as e:
            raise Exception(f"Erreur action système: {str(e)}")
    
    @staticmethod
    def get_uptime_formatted() -> str:
        """Retourne l'uptime formaté"""
        try:
            uptime_seconds = datetime.now().timestamp() - psutil.boot_time()
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            if days > 0:
                return f"{days}j {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except Exception as e:
            return "Inconnu"
    
    @staticmethod
    def get_system_users() -> List[dict]:
        """Récupère la liste des utilisateurs connectés"""
        try:
            users = []
            for user in psutil.users():
                users.append({
                    "name": user.name,
                    "terminal": user.terminal,
                    "host": user.host,
                    "started": datetime.fromtimestamp(user.started).isoformat(),
                    "pid": user.pid if hasattr(user, 'pid') else None
                })
            return users
        except Exception as e:
            raise Exception(f"Erreur récupération utilisateurs: {str(e)}")
    
    @staticmethod
    def check_system_health() -> dict:
        """Vérifie la santé générale du système"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_status = "OK" if cpu_percent < 80 else "WARN" if cpu_percent < 95 else "CRITICAL"
            
            # Mémoire
            memory = psutil.virtual_memory()
            mem_status = "OK" if memory.percent < 80 else "WARN" if memory.percent < 95 else "CRITICAL"
            
            # Disque
            disk_usage = psutil.disk_usage('/')
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            disk_status = "OK" if disk_percent < 80 else "WARN" if disk_percent < 95 else "CRITICAL"
            
            # Load average
            load1, _, _ = os.getloadavg()
            cpu_count = psutil.cpu_count()
            load_ratio = load1 / cpu_count
            load_status = "OK" if load_ratio < 0.7 else "WARN" if load_ratio < 1.0 else "CRITICAL"
            
            # Statut global
            statuses = [cpu_status, mem_status, disk_status, load_status]
            if "CRITICAL" in statuses:
                overall_status = "CRITICAL"
            elif "WARN" in statuses:
                overall_status = "WARN"
            else:
                overall_status = "OK"
            
            return {
                "overall_status": overall_status,
                "cpu": {"percent": cpu_percent, "status": cpu_status},
                "memory": {"percent": memory.percent, "status": mem_status},
                "disk": {"percent": disk_percent, "status": disk_status},
                "load": {"ratio": load_ratio, "status": load_status},
                "uptime": SystemService.get_uptime_formatted(),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise Exception(f"Erreur vérification santé système: {str(e)}")