from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import psutil
import socket
from models.network import NetworkInterface, NetworkIOStats, NetworkConnection, NetworkSummary

router = APIRouter(
    prefix="/network",
    tags=["Network"],
    responses={404: {"description": "Not found"}}
)

class NetworkService:
    """Service pour gérer les informations réseau"""
    
    @staticmethod
    def get_network_interfaces() -> List[NetworkInterface]:
        """Récupère la liste des interfaces réseau"""
        try:
            interfaces = []
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()
            
            for interface_name, interface_addrs in addrs.items():
                # Récupérer les adresses IP
                addresses = []
                for addr in interface_addrs:
                    if addr.family == socket.AF_INET:  # IPv4
                        addresses.append(addr.address)
                    elif addr.family == socket.AF_INET6:  # IPv6
                        addresses.append(addr.address)
                
                # Récupérer les statistiques
                interface_stats = stats.get(interface_name)
                is_up = interface_stats.isup if interface_stats else False
                speed = interface_stats.speed if interface_stats else None
                mtu = interface_stats.mtu if interface_stats else None
                
                interfaces.append(NetworkInterface(
                    name=interface_name,
                    addresses=addresses,
                    is_up=is_up,
                    speed=speed if speed and speed > 0 else None,
                    mtu=mtu
                ))
            
            return interfaces
        except Exception as e:
            raise Exception(f"Erreur récupération interfaces réseau: {str(e)}")
    
    @staticmethod
    def get_network_io_stats() -> List[NetworkIOStats]:
        """Récupère les statistiques I/O réseau"""
        try:
            network_stats = []
            stats = psutil.net_io_counters(pernic=True)
            
            for interface, stat in stats.items():
                network_stats.append(NetworkIOStats(
                    interface=interface,
                    bytes_sent=stat.bytes_sent,
                    bytes_recv=stat.bytes_recv,
                    packets_sent=stat.packets_sent,
                    packets_recv=stat.packets_recv,
                    errin=stat.errin,
                    errout=stat.errout,
                    dropin=stat.dropin,
                    dropout=stat.dropout
                ))
            
            return network_stats
        except Exception as e:
            raise Exception(f"Erreur récupération stats I/O réseau: {str(e)}")
    
    @staticmethod
    def get_network_connections(kind: str = "inet") -> List[NetworkConnection]:
        """Récupère les connexions réseau actives"""
        try:
            connections = []
            conns = psutil.net_connections(kind=kind)
            
            for conn in conns:
                # Parser l'adresse locale
                local_addr = conn.laddr.ip if conn.laddr else None
                local_port = conn.laddr.port if conn.laddr else None
                
                # Parser l'adresse distante
                remote_addr = conn.raddr.ip if conn.raddr else None
                remote_port = conn.raddr.port if conn.raddr else None
                
                # Déterminer la famille et le type
                family_map = {
                    socket.AF_INET: "AF_INET",
                    socket.AF_INET6: "AF_INET6"
                }
                type_map = {
                    socket.SOCK_STREAM: "SOCK_STREAM",
                    socket.SOCK_DGRAM: "SOCK_DGRAM"
                }
                
                connections.append(NetworkConnection(
                    fd=conn.fd,
                    family=family_map.get(conn.family, "UNKNOWN"),
                    type=type_map.get(conn.type, "UNKNOWN"),
                    local_address=local_addr or "",
                    local_port=local_port or 0,
                    remote_address=remote_addr,
                    remote_port=remote_port,
                    status=conn.status,
                    pid=conn.pid
                ))
            
            return connections
        except Exception as e:
            raise Exception(f"Erreur récupération connexions réseau: {str(e)}")
    
    @staticmethod
    def get_listening_ports() -> List[int]:
        """Récupère la liste des ports en écoute"""
        try:
            listening_ports = set()
            connections = psutil.net_connections(kind="inet")
            
            for conn in connections:
                if conn.status == psutil.CONN_LISTEN and conn.laddr:
                    listening_ports.add(conn.laddr.port)
            
            return sorted(list(listening_ports))
        except Exception as e:
            raise Exception(f"Erreur récupération ports en écoute: {str(e)}")
    
    @staticmethod
    def get_network_summary() -> NetworkSummary:
        """Récupère un résumé du réseau"""
        try:
            interfaces = NetworkService.get_network_interfaces()
            io_stats = NetworkService.get_network_io_stats()
            connections = NetworkService.get_network_connections()
            listening_ports = NetworkService.get_listening_ports()
            
            return NetworkSummary(
                interfaces=interfaces,
                io_stats=io_stats,
                active_connections=len(connections),
                listening_ports=listening_ports
            )
        except Exception as e:
            raise Exception(f"Erreur récupération résumé réseau: {str(e)}")

@router.get("/interfaces", response_model=List[NetworkInterface])
async def get_network_interfaces():
    """
    Récupère la liste de toutes les interfaces réseau
    
    Pour chaque interface:
    - **name**: Nom de l'interface (eth0, wlan0, etc.)
    - **addresses**: Liste des adresses IP (IPv4/IPv6)
    - **is_up**: Interface active ou non
    - **speed**: Vitesse en Mbps (si disponible)
    - **mtu**: Maximum Transmission Unit
    """
    try:
        return NetworkService.get_network_interfaces()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/interfaces/{interface_name}")
async def get_interface_details(interface_name: str):
    """
    Récupère les détails d'une interface spécifique
    """
    try:
        interfaces = NetworkService.get_network_interfaces()
        interface = next((iface for iface in interfaces if iface.name == interface_name), None)
        
        if not interface:
            raise HTTPException(status_code=404, detail=f"Interface {interface_name} non trouvée")
        
        # Récupérer les stats I/O pour cette interface
        io_stats = NetworkService.get_network_io_stats()
        interface_io = next((stat for stat in io_stats if stat.interface == interface_name), None)
        
        return {
            "interface": interface,
            "io_stats": interface_io
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/io", response_model=List[NetworkIOStats])
async def get_network_io_stats():
    """
    Récupère les statistiques I/O de toutes les interfaces réseau
    
    Pour chaque interface:
    - **bytes_sent/recv**: Bytes envoyés/reçus
    - **packets_sent/recv**: Paquets envoyés/reçus
    - **errin/errout**: Erreurs entrée/sortie
    - **dropin/dropout**: Paquets perdus entrée/sortie
    """
    try:
        return NetworkService.get_network_io_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/connections", response_model=List[NetworkConnection])
async def get_network_connections(
    kind: str = Query(default="inet", regex="^(inet|inet4|inet6|tcp|tcp4|tcp6|udp|udp4|udp6|unix|all)$"),
    limit: Optional[int] = Query(default=None, ge=1, le=1000)
):
    """
    Récupère les connexions réseau actives
    
    - **kind**: Type de connexions (inet, tcp, udp, unix, all)
    - **limit**: Nombre maximum de connexions à retourner
    
    Pour chaque connexion:
    - **fd**: File descriptor
    - **family**: Famille d'adresses (AF_INET, AF_INET6)
    - **type**: Type de socket (SOCK_STREAM, SOCK_DGRAM)
    - **local_address/port**: Adresse/port local
    - **remote_address/port**: Adresse/port distant
    - **status**: État de la connexion
    - **pid**: ID du processus propriétaire
    """
    try:
        connections = NetworkService.get_network_connections(kind=kind)
        
        if limit:
            connections = connections[:limit]
        
        return connections
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ports/listening")
async def get_listening_ports():
    """
    Récupère la liste des ports en écoute
    """
    try:
        ports = NetworkService.get_listening_ports()
        return {"listening_ports": ports, "count": len(ports)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ports/{port}")
async def get_port_info(port: int):
    """
    Récupère les informations d'un port spécifique
    """
    try:
        connections = NetworkService.get_network_connections()
        port_connections = [
            conn for conn in connections 
            if conn.local_port == port or conn.remote_port == port
        ]
        
        # Vérifier si le port est en écoute
        listening_ports = NetworkService.get_listening_ports()
        is_listening = port in listening_ports
        
        return {
            "port": port,
            "is_listening": is_listening,
            "connections": port_connections,
            "connection_count": len(port_connections)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary", response_model=NetworkSummary)
async def get_network_summary():
    """
    Récupère un résumé complet du réseau
    
    Inclut:
    - Toutes les interfaces et leurs statistiques
    - Nombre de connexions actives
    - Liste des ports en écoute
    """
    try:
        return NetworkService.get_network_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bandwidth")
async def get_network_bandwidth():
    """
    Calcule l'utilisation de la bande passante
    """
    try:
        import time
        
        # Première mesure
        stats1 = NetworkService.get_network_io_stats()
        time.sleep(1)  # Attendre 1 seconde
        stats2 = NetworkService.get_network_io_stats()
        
        bandwidth = []
        for i, stat1 in enumerate(stats1):
            if i < len(stats2):
                stat2 = stats2[i]
                if stat1.interface == stat2.interface:
                    # Calculer les différences par seconde
                    bytes_sent_per_sec = stat2.bytes_sent - stat1.bytes_sent
                    bytes_recv_per_sec = stat2.bytes_recv - stat1.bytes_recv
                    
                    bandwidth.append({
                        "interface": stat1.interface,
                        "bytes_sent_per_sec": bytes_sent_per_sec,
                        "bytes_recv_per_sec": bytes_recv_per_sec,
                        "mbps_sent": round(bytes_sent_per_sec * 8 / 1_000_000, 2),
                        "mbps_recv": round(bytes_recv_per_sec * 8 / 1_000_000, 2)
                    })
        
        return {"bandwidth": bandwidth}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ping/{host}")
async def ping_host(host: str):
    """
    Ping un hôte distant
    """
    try:
        import subprocess
        import re
        
        # Valider l'hôte (sécurité)
        if not re.match(r'^[a-zA-Z0-9\-\.]+', host):
            raise HTTPException(status_code=400, detail="Nom d'hôte invalide")
        
        # Exécuter ping
        result = subprocess.run(
            ['ping', '-c', '4', host],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        success = result.returncode == 0
        
        # Parser les résultats
        output_lines = result.stdout.strip().split('\n')
        stats = {}
        
        if success and len(output_lines) > 0:
            # Extraire les statistiques
            for line in output_lines:
                if "packet loss" in line:
                    loss_match = re.search(r'(\d+)% packet loss', line)
                    if loss_match:
                        stats["packet_loss"] = int(loss_match.group(1))
                elif "min/avg/max" in line:
                    time_match = re.search(r'min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)', line)
                    if time_match:
                        stats["min_time"] = float(time_match.group(1))
                        stats["avg_time"] = float(time_match.group(2))
                        stats["max_time"] = float(time_match.group(3))
        
        return {
            "host": host,
            "success": success,
            "output": result.stdout,
            "error": result.stderr if result.stderr else None,
            "stats": stats
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Timeout lors du ping")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def check_network_health():
    """
    Vérifie la santé du réseau
    """
    try:
        interfaces = NetworkService.get_network_interfaces()
        io_stats = NetworkService.get_network_io_stats()
        
        health_report = {
            "overall_status": "OK",
            "issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Vérifier les interfaces
        active_interfaces = [iface for iface in interfaces if iface.is_up and iface.name != "lo"]
        if len(active_interfaces) == 0:
            health_report["issues"].append("Aucune interface réseau active")
            health_report["overall_status"] = "CRITICAL"
        
        # Vérifier les erreurs réseau
        for stat in io_stats:
            if stat.interface != "lo":  # Ignorer loopback
                total_packets = stat.packets_sent + stat.packets_recv
                total_errors = stat.errin + stat.errout
                total_drops = stat.dropin + stat.dropout
                
                if total_packets > 0:
                    error_rate = total_errors / total_packets
                    drop_rate = total_drops / total_packets
                    
                    if error_rate > 0.01:  # > 1% d'erreurs
                        health_report["warnings"].append(
                            f"Taux d'erreur élevé sur {stat.interface}: {error_rate:.2%}"
                        )
                        if health_report["overall_status"] == "OK":
                            health_report["overall_status"] = "WARN"
                    
                    if drop_rate > 0.01:  # > 1% de paquets perdus
                        health_report["warnings"].append(
                            f"Taux de perte élevé sur {stat.interface}: {drop_rate:.2%}"
                        )
                        if health_report["overall_status"] == "OK":
                            health_report["overall_status"] = "WARN"
        
        # Recommandations
        if len(active_interfaces) == 1:
            health_report["recommendations"].append("Considérer une interface réseau de secours")
        
        return health_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))