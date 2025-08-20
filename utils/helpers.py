import os
import re
import subprocess
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Tuple
from functools import wraps
import psutil
import logging

logger = logging.getLogger("vps_manager.helpers")

class SystemHelpers:
    """Utilitaires système essentiels"""
    
    @staticmethod
    def bytes_to_human(bytes_value: int) -> str:
        """Convertir des bytes en format lisible"""
        if bytes_value == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = bytes_value
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"
    
    @staticmethod
    def seconds_to_human(seconds: float) -> str:
        """Convertir des secondes en format lisible"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        
        minutes = seconds / 60
        if minutes < 60:
            return f"{minutes:.1f}m"
        
        hours = minutes / 60
        if hours < 24:
            return f"{hours:.1f}h"
        
        days = hours / 24
        return f"{days:.1f}j"
    
    @staticmethod
    def safe_command(command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """Exécuter une commande de manière sécurisée"""
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, 
                text=True, timeout=timeout, check=False
            )
            return (result.returncode == 0, result.stdout.strip(), result.stderr.strip())
        except subprocess.TimeoutExpired:
            return False, "", f"Timeout après {timeout}s"
        except Exception as e:
            return False, "", str(e)

class ValidationHelpers:
    """Utilitaires de validation"""
    
    @staticmethod
    def validate_service_name(service_name: str) -> bool:
        """Valider un nom de service"""
        return bool(service_name and 
                   len(service_name) <= 100 and 
                   re.match(r'^[a-zA-Z0-9\-_.@]+$', service_name))
    
    @staticmethod
    def validate_ip(ip: str) -> bool:
        """Valider une adresse IP"""
        try:
            import ipaddress
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_port(port: Union[str, int]) -> bool:
        """Valider un port"""
        try:
            return 1 <= int(port) <= 65535
        except (ValueError, TypeError):
            return False

class CacheHelpers:
    """Cache simple en mémoire"""
    
    _cache: Dict[str, Dict[str, Any]] = {}
    
    @staticmethod
    def get(key: str) -> Optional[Any]:
        """Récupérer du cache"""
        if key in CacheHelpers._cache:
            entry = CacheHelpers._cache[key]
            if entry["expires"] > time.time():
                return entry["value"]
            else:
                del CacheHelpers._cache[key]
        return None
    
    @staticmethod
    def set(key: str, value: Any, ttl: int = 300) -> None:
        """Stocker en cache"""
        CacheHelpers._cache[key] = {
            "value": value,
            "expires": time.time() + ttl
        }
    
    @staticmethod
    def clear() -> None:
        """Vider le cache"""
        CacheHelpers._cache.clear()

class AlertHelpers:
    """Système d'alertes simple"""
    
    @staticmethod
    def check_threshold(value: float, warning: float, critical: float) -> str:
        """Vérifier les seuils"""
        if value >= critical:
            return "CRITICAL"
        elif value >= warning:
            return "WARNING"
        else:
            return "OK"
    
    @staticmethod
    def create_alert(metric: str, value: float, threshold: float, level: str) -> str:
        """Créer un message d'alerte"""
        emoji = {"CRITICAL": "🚨", "WARNING": "⚠️", "OK": "✅"}.get(level, "ℹ️")
        return f"{emoji} {level}: {metric} = {value}% (seuil: {threshold}%)"

class FileHelpers:
    """Utilitaires fichiers"""
    
    @staticmethod
    def read_safe(filepath: str, max_size: int = 10*1024*1024) -> Optional[str]:
        """Lire un fichier en sécurité"""
        try:
            if not os.path.exists(filepath) or os.path.getsize(filepath) > max_size:
                return None
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Erreur lecture {filepath}: {e}")
            return None
    
    @staticmethod
    def tail(filepath: str, lines: int = 10) -> List[str]:
        """Lire les dernières lignes d'un fichier"""
        success, stdout, stderr = SystemHelpers.safe_command(f"tail -n {lines} '{filepath}'")
        return stdout.split('\n') if success else []

class NetworkHelpers:
    """Utilitaires réseau"""
    
    @staticmethod
    def ping(host: str, count: int = 4) -> Dict[str, Any]:
        """Ping un hôte"""
        success, stdout, stderr = SystemHelpers.safe_command(f"ping -c {count} {host}")
        
        result = {
            "host": host,
            "success": success,
            "packet_loss": 100.0,
            "avg_time": None
        }
        
        if success and stdout:
            # Parser packet loss
            for line in stdout.split('\n'):
                if "packet loss" in line:
                    match = re.search(r'(\d+)% packet loss', line)
                    if match:
                        result["packet_loss"] = float(match.group(1))
                elif "min/avg/max" in line:
                    match = re.search(r'min/avg/max.*?= [\d.]+/([\d.]+)/[\d.]+', line)
                    if match:
                        result["avg_time"] = float(match.group(1))
        
        return result
    
    @staticmethod
    def is_port_open(host: str, port: int, timeout: float = 3.0) -> bool:
        """Tester si un port est ouvert"""
        import socket
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, socket.error):
            return False

# Décorateurs utiles
def cached(ttl: int = 300):
    """Cache automatique pour les fonctions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            result = CacheHelpers.get(key)
            if result is None:
                result = func(*args, **kwargs)
                CacheHelpers.set(key, result, ttl)
            return result
        return wrapper
    return decorator

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Retry automatique en cas d'échec"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        raise e
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

def measure_time(func):
    """Mesurer le temps d'exécution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logger.info(f"{func.__name__} exécuté en {end - start:.3f}s")
        return result
    return wrapper

# Fonctions utilitaires
def format_table(data: List[Dict], headers: Optional[List[str]] = None) -> str:
    """Formater des données en tableau"""
    if not data:
        return "Aucune donnée"
    
    if not headers:
        headers = list(data[0].keys())
    
    # Calculer largeurs
    widths = {h: len(h) for h in headers}
    for row in data:
        for h in headers:
            if h in row:
                widths[h] = max(widths[h], len(str(row[h])))
    
    # Construire tableau
    lines = []
    header_line = " | ".join(h.ljust(widths[h]) for h in headers)
    lines.append(header_line)
    lines.append("-" * len(header_line))
    
    for row in data:
        line = " | ".join(str(row.get(h, "")).ljust(widths[h]) for h in headers)
        lines.append(line)
    
    return "\n".join(lines)

def create_summary(data: Dict[str, Any]) -> str:
    """Créer un résumé simple"""
    lines = []
    lines.append("=" * 40)
    lines.append("  RÉSUMÉ VPS")
    lines.append("=" * 40)
    lines.append(f"Généré: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    if "system" in data:
        sys = data["system"]
        lines.append(f"🖥️  Système: {sys.get('hostname', 'N/A')}")
        lines.append(f"   Uptime: {sys.get('uptime_formatted', 'N/A')}")
        lines.append("")
    
    if "hardware" in data:
        hw = data["hardware"]
        if "cpu" in hw:
            lines.append(f"🔧 CPU: {hw['cpu'].get('usage_percent', 'N/A')}%")
        if "memory" in hw:
            lines.append(f"💾 RAM: {hw['memory'].get('usage_percent', 'N/A')}%")
        lines.append("")
    
    if "health" in data:
        status = data["health"].get("overall_status", "UNKNOWN")
        emoji = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "🚨"}.get(status, "❓")
        lines.append(f"💊 Santé: {emoji} {status}")
    
    lines.append("=" * 40)
    return "\n".join(lines)

def safe_execute(func, default=None, *args, **kwargs):
    """Exécuter une fonction en sécurité"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Erreur {func.__name__}: {e}")
        return default

def get_health_color(status: str) -> str:
    """Couleur pour un statut de santé"""
    colors = {"OK": "🟢", "WARNING": "🟡", "CRITICAL": "🔴"}
    return colors.get(status.upper(), "⚪")

def cleanup_cache():
    """Nettoyer le cache expiré"""
    current_time = time.time()
    expired_keys = [
        key for key, entry in CacheHelpers._cache.items()
        if entry["expires"] <= current_time
    ]
    for key in expired_keys:
        del CacheHelpers._cache[key]
    return len(expired_keys)