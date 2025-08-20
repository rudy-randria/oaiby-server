import psutil
import shutil
from typing import List, Optional, Dict
from models.hardware import (
    CPUInfo, MemoryInfo, SwapInfo, DiskInfo, 
    DiskIOStats, TemperatureInfo
)

class HardwareService:
    """Service pour gérer les informations hardware"""
    
    @staticmethod
    def get_cpu_info() -> CPUInfo:
        """Récupère les informations CPU"""
        try:
            # Informations de base
            cpu_count_physical = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            
            # Fréquences
            cpu_freq = psutil.cpu_freq()
            freq_current = cpu_freq.current if cpu_freq else None
            freq_max = cpu_freq.max if cpu_freq else None
            freq_min = cpu_freq.min if cpu_freq else None
            
            # Utilisation globale et par cœur
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_percent_per_core = psutil.cpu_percent(interval=1, percpu=True)
            
            # Température (si disponible)
            temp = HardwareService._get_cpu_temperature()
            
            return CPUInfo(
                count=cpu_count_physical or cpu_count_logical,
                count_logical=cpu_count_logical,
                percent=cpu_percent,
                freq_current=freq_current,
                freq_max=freq_max,
                freq_min=freq_min,
                temp=temp,
                usage_per_core=cpu_percent_per_core
            )
        except Exception as e:
            raise Exception(f"Erreur récupération info CPU: {str(e)}")
    
    @staticmethod
    def _get_cpu_temperature() -> Optional[float]:
        """Récupère la température CPU si disponible"""
        try:
            temps = psutil.sensors_temperatures()
            
            # Essayer différentes sources de température
            temp_sources = ['coretemp', 'cpu_thermal', 'k10temp', 'zenpower']
            
            for source in temp_sources:
                if source in temps and temps[source]:
                    return temps[source][0].current
            
            # Si aucune source spécifique, prendre la première disponible
            for sensor_list in temps.values():
                if sensor_list:
                    return sensor_list[0].current
                    
            return None
        except:
            return None
    
    @staticmethod
    def get_memory_info() -> MemoryInfo:
        """Récupère les informations mémoire"""
        try:
            memory = psutil.virtual_memory()
            
            return MemoryInfo(
                total=memory.total,
                available=memory.available,
                percent=memory.percent,
                used=memory.used,
                free=memory.free,
                cached=getattr(memory, 'cached', None),
                buffers=getattr(memory, 'buffers', None)
            )
        except Exception as e:
            raise Exception(f"Erreur récupération info mémoire: {str(e)}")
    
    @staticmethod
    def get_swap_info() -> SwapInfo:
        """Récupère les informations swap"""
        try:
            swap = psutil.swap_memory()
            
            return SwapInfo(
                total=swap.total,
                used=swap.used,
                free=swap.free,
                percent=swap.percent,
                sin=swap.sin,
                sout=swap.sout
            )
        except Exception as e:
            raise Exception(f"Erreur récupération info swap: {str(e)}")
    
    @staticmethod
    def get_disk_info() -> List[DiskInfo]:
        """Récupère les informations des disques"""
        try:
            disks = []
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    # Ignorer les systèmes de fichiers virtuels
                    if partition.fstype in ['tmpfs', 'devtmpfs', 'proc', 'sysfs', 'cgroup', 'cgroup2']:
                        continue
                    
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    disks.append(DiskInfo(
                        mountpoint=partition.mountpoint,
                        device=partition.device,
                        fstype=partition.fstype,
                        total=usage.total,
                        used=usage.used,
                        free=usage.free,
                        percent=(usage.used / usage.total) * 100 if usage.total > 0 else 0
                    ))
                except (PermissionError, OSError):
                    # Ignorer les partitions inaccessibles
                    continue
                    
            return disks
        except Exception as e:
            raise Exception(f"Erreur récupération info disque: {str(e)}")
    
    @staticmethod
    def get_disk_io_stats() -> List[DiskIOStats]:
        """Récupère les statistiques I/O des disques"""
        try:
            disk_stats = []
            disk_io = psutil.disk_io_counters(perdisk=True)
            
            if disk_io:
                for device, stats in disk_io.items():
                    # Filtrer les devices de loop et autres virtuels
                    if not device.startswith(('loop', 'ram', 'dm-')):
                        disk_stats.append(DiskIOStats(
                            device=device,
                            read_count=stats.read_count,
                            write_count=stats.write_count,
                            read_bytes=stats.read_bytes,
                            write_bytes=stats.write_bytes,
                            read_time=stats.read_time,
                            write_time=stats.write_time
                        ))
            
            return disk_stats
        except Exception as e:
            raise Exception(f"Erreur récupération stats I/O disque: {str(e)}")
    
    @staticmethod
    def get_temperature_info() -> List[TemperatureInfo]:
        """Récupère toutes les informations de température"""
        try:
            temps = []
            
            try:
                sensors = psutil.sensors_temperatures()
                
                for sensor_name, sensor_list in sensors.items():
                    for i, sensor in enumerate(sensor_list):
                        label = f"{sensor_name}_{i}" if len(sensor_list) > 1 else sensor_name
                        if hasattr(sensor, 'label') and sensor.label:
                            label = sensor.label
                        
                        temps.append(TemperatureInfo(
                            label=label,
                            current=sensor.current,
                            high=getattr(sensor, 'high', None),
                            critical=getattr(sensor, 'critical', None)
                        ))
            except AttributeError:
                # sensors_temperatures() n'est pas disponible sur ce système
                pass
            
            return temps
        except Exception as e:
            raise Exception(f"Erreur récupération températures: {str(e)}")
    
    @staticmethod
    def get_hardware_summary() -> Dict:
        """Récupère un résumé complet du hardware"""
        try:
            # CPU
            cpu = HardwareService.get_cpu_info()
            
            # Mémoire
            memory = HardwareService.get_memory_info()
            swap = HardwareService.get_swap_info()
            
            # Disques
            disks = HardwareService.get_disk_info()
            total_disk_space = sum(disk.total for disk in disks)
            used_disk_space = sum(disk.used for disk in disks)
            
            # Températures
            temps = HardwareService.get_temperature_info()
            max_temp = max(temp.current for temp in temps) if temps else None
            
            return {
                "cpu": {
                    "cores": cpu.count,
                    "logical_cores": cpu.count_logical,
                    "usage_percent": cpu.percent,
                    "frequency_mhz": cpu.freq_current,
                    "temperature_c": cpu.temp
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory.percent
                },
                "swap": {
                    "total_gb": round(swap.total / (1024**3), 2),
                    "used_gb": round(swap.used / (1024**3), 2),
                    "usage_percent": swap.percent
                },
                "storage": {
                    "total_gb": round(total_disk_space / (1024**3), 2),
                    "used_gb": round(used_disk_space / (1024**3), 2),
                    "free_gb": round((total_disk_space - used_disk_space) / (1024**3), 2),
                    "usage_percent": round((used_disk_space / total_disk_space) * 100, 2) if total_disk_space > 0 else 0,
                    "partitions_count": len(disks)
                },
                "thermal": {
                    "max_temperature_c": max_temp,
                    "sensors_count": len(temps)
                }
            }
        except Exception as e:
            raise Exception(f"Erreur récupération résumé hardware: {str(e)}")
    
    @staticmethod
    def check_hardware_health() -> Dict:
        """Vérifie la santé du hardware"""
        try:
            health_report = {
                "overall_status": "OK",
                "issues": [],
                "warnings": [],
                "recommendations": []
            }
            
            # Vérifier CPU
            cpu = HardwareService.get_cpu_info()
            if cpu.percent > 90:
                health_report["issues"].append(f"CPU usage très élevé: {cpu.percent}%")
                health_report["overall_status"] = "CRITICAL"
            elif cpu.percent > 75:
                health_report["warnings"].append(f"CPU usage élevé: {cpu.percent}%")
                if health_report["overall_status"] == "OK":
                    health_report["overall_status"] = "WARN"
            
            # Vérifier température CPU
            if cpu.temp and cpu.temp > 80:
                health_report["issues"].append(f"Température CPU élevée: {cpu.temp}°C")
                health_report["overall_status"] = "CRITICAL"
            elif cpu.temp and cpu.temp > 70:
                health_report["warnings"].append(f"Température CPU modérée: {cpu.temp}°C")
                if health_report["overall_status"] == "OK":
                    health_report["overall_status"] = "WARN"
            
            # Vérifier mémoire
            memory = HardwareService.get_memory_info()
            if memory.percent > 95:
                health_report["issues"].append(f"Mémoire critique: {memory.percent}%")
                health_report["overall_status"] = "CRITICAL"
            elif memory.percent > 85:
                health_report["warnings"].append(f"Mémoire élevée: {memory.percent}%")
                if health_report["overall_status"] == "OK":
                    health_report["overall_status"] = "WARN"
            
            # Vérifier swap
            swap = HardwareService.get_swap_info()
            if swap.total > 0 and swap.percent > 50:
                health_report["warnings"].append(f"Utilisation swap élevée: {swap.percent}%")
                if health_report["overall_status"] == "OK":
                    health_report["overall_status"] = "WARN"
            
            # Vérifier disques
            disks = HardwareService.get_disk_info()
            for disk in disks:
                if disk.percent > 95:
                    health_report["issues"].append(f"Disque {disk.mountpoint} critique: {disk.percent}%")
                    health_report["overall_status"] = "CRITICAL"
                elif disk.percent > 85:
                    health_report["warnings"].append(f"Disque {disk.mountpoint} plein: {disk.percent}%")
                    if health_report["overall_status"] == "OK":
                        health_report["overall_status"] = "WARN"
            
            # Recommandations
            if memory.percent > 80:
                health_report["recommendations"].append("Considérer l'ajout de mémoire RAM")
            
            if any(disk.percent > 80 for disk in disks):
                health_report["recommendations"].append("Nettoyer l'espace disque ou ajouter du stockage")
            
            if cpu.percent > 80:
                health_report["recommendations"].append("Vérifier les processus consommateurs de CPU")
            
            return health_report
        except Exception as e:
            raise Exception(f"Erreur vérification santé hardware: {str(e)}")