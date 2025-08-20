"""
VPS Resource Manager API
API FastAPI pour gérer les ressources d'un VPS Ubuntu
"""

# Métadonnées du package
__title__ = "VPS Resource Manager API"
__version__ = "2.0.0"
__author__ = "VPS Manager Team"
__description__ = "API FastAPI pour gérer les ressources d'un VPS Ubuntu"

def get_version():
    """Retourner la version"""
    return __version__

def get_app_info():
    """Retourner les infos de l'app"""
    return {
        "title": __title__,
        "version": __version__,
        "author": __author__,
        "description": __description__
    }

def check_dependencies():
    """Vérifier les dépendances essentielles"""
    missing = []
    
    try:
        import fastapi
    except ImportError:
        missing.append("fastapi")
    
    try:
        import uvicorn
    except ImportError:
        missing.append("uvicorn")
    
    if missing:
        print(f"❌ Dépendances manquantes: {', '.join(missing)}")
        print("💡 Installez avec: pip install fastapi uvicorn psutil")
        return False
    
    return True

# Vérification au démarrage
if not check_dependencies():
    pass  # Continue même si dépendances manquantes

# Exports
__all__ = ["__version__", "__title__", "get_version", "get_app_info"]