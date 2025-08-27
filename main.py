#!/usr/bin/env python3
"""VPS Resource Manager API - Point d'entrée principal"""

import sys
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ajouter le dossier racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

def create_app():
    """Créer l'application FastAPI"""
    app = FastAPI(
        title="VPS Resource Manager API",
        description="API pour gérer les ressources d'un VPS Ubuntu",
        version="2.0.0"
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import routers (si ils existent)
    try:
        from routers.auth import router as auth_router
        app.include_router(auth_router)
    except ImportError as e:
        print(f"⚠️  Erreur d'import des routers: {e}")
        pass

    try:
        from routers.system import router as system_router
        app.include_router(system_router)
    except ImportError as e:
        print(f"⚠️  Erreur d'import des routers: {e}")
        pass

    try:
        from routers.hardware import router as hardware_router
        app.include_router(hardware_router)
    except ImportError as e:
        print(f"⚠️  Erreur d'import des routers: {e}")
        pass

    try:
        from routers.network import router as network_router
        app.include_router(network_router)
    except ImportError as e:
        print(f"⚠️  Erreur d'import des routers: {e}")
        pass

    try:
        from routers.services import router as services_router
        app.include_router(services_router)
    except ImportError as e:
        print(f"⚠️  Erreur d'import des routers: {e}")
        pass

    # Routes de base
    @app.get("/")
    async def root():
        return {
            "message": "VPS Resource Manager API",
            "version": "2.0.0",
            "status": "running",
            "docs": "/docs"
        }

    @app.get("/health")
    async def health():
        try:
            import psutil
            return {
                "status": "OK",
                "cpu": f"{psutil.cpu_percent(interval=1)}%",
                "memory": f"{psutil.virtual_memory().percent}%"
            }
        except ImportError:
            return {"status": "OK", "note": "psutil non installé"}
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

    return app

def main():
    """Point d'entrée avec arguments simples"""
    import argparse
    
    parser = argparse.ArgumentParser(description="VPS Resource Manager API")
    parser.add_argument("--host", default="0.0.0.0", help="Host (défaut: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port (défaut: 8000)")
    parser.add_argument("--reload", action="store_true", help="Mode dev avec reload")
    
    args = parser.parse_args()
    
    print(f"🚀 VPS Manager API démarrage sur http://{args.host}:{args.port}")
    print(f"📚 Documentation: http://{args.host}:{args.port}/docs")
    
    app = create_app()
    
    try:
        uvicorn.run(app, host=args.host, port=args.port, reload=args.reload)
    except KeyboardInterrupt:
        print("\n👋 Arrêt de l'API")

if __name__ == "__main__":
    main()