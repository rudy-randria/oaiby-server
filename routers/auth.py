"""Routes d'authentification pour l'API VPS Manager"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime

from models.auth import (
    LoginRequest,
    LoginResponse,
    UserInfo,
    LogoutResponse,
    ErrorResponse,
    CreateUserRequest,
    UpdateUserRequest,
    ChangePasswordRequest
)

# Import du service simple (sans PostgreSQL pour éviter les erreurs)
try:
    from services.auth_service_simple import AuthService
    print("✅ Utilisation du service d'auth simple")
except ImportError:
    try:
        from services.auth_service import AuthService
        print("✅ Utilisation du service d'auth PostgreSQL")
    except ImportError:
        print("❌ Aucun service d'auth trouvé")
        raise

# Configuration du router
router = APIRouter(
    prefix="/api/auth",
    tags=["authentification"],
    responses={
        401: {"model": ErrorResponse, "description": "Non authentifié"},
        403: {"model": ErrorResponse, "description": "Accès interdit"}
    }
)

# Sécurité Bearer Token
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInfo:
    """Dépendance pour obtenir l'utilisateur actuel depuis le token"""
    return AuthService.verify_token(credentials.credentials)

def get_admin_user(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Dépendance pour vérifier que l'utilisateur est admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits administrateur requis"
        )
    return current_user

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """
    Connexion utilisateur

    Authentifie un utilisateur et retourne un token JWT.

    **Compte de test:**
    - `admin` / `password` (administrateur)
    """
    user = AuthService.authenticate_user(login_data.username, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect"
        )

    # Gérer les différents formats de données utilisateur
    if hasattr(user, 'username'):  # SQLAlchemy User object
        token = AuthService.create_access_token(user)
        full_name = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip()
        if not full_name:
            full_name = user.username

        user_data = {
            "username": user.username,
            "is_admin": user.is_admin,
            "uuid": getattr(user, 'uuid', f"uuid-{user.username}"),
            "full_name": full_name
        }
    else:  # Dictionary (simple auth)
        token = AuthService.create_access_token(user, login_data.username)
        full_name = f"{user.get('first_name', '') or ''} {user.get('last_name', '') or ''}".strip()
        if not full_name:
            full_name = login_data.username

        user_data = {
            "username": login_data.username,
            "is_admin": user["is_admin"],
            "uuid": user.get("uuid", f"uuid-{login_data.username}"),
            "full_name": full_name
        }

    return LoginResponse(
        token=token,
        token_type="bearer",
        expires_in=AuthService.get_token_expire_time(),
        user=user_data
    )

@router.get("/me", response_model=dict)
async def get_current_user_info(current_user: UserInfo = Depends(get_current_user)):
    """
    Obtenir les informations de l'utilisateur connecté

    Retourne les informations détaillées de l'utilisateur authentifié.
    """
    # Essayer d'obtenir plus de détails depuis le service
    try:
        if hasattr(AuthService, 'get_user_by_username'):
            user_data = AuthService.get_user_by_username(current_user.username)
        else:
            user_data = AuthService.get_user(current_user.username)

        if user_data:
            if hasattr(user_data, 'to_dict'):  # SQLAlchemy
                result = user_data.to_dict()
                result.pop('password_hash', None)
                result.pop('password_reset_token', None)
                return result
            else:  # Dictionary
                result = {k: v for k, v in user_data.items() if k != 'password_hash'}
                return result
    except Exception:
        pass

    # Fallback sur les données du token
    return {
        "username": current_user.username,
        "is_admin": current_user.is_admin,
        "created_at": current_user.created_at,
        "last_login": current_user.last_login
    }

@router.post("/logout", response_model=LogoutResponse)
async def logout(current_user: UserInfo = Depends(get_current_user)):
    """
    Déconnexion utilisateur

    La déconnexion est principalement gérée côté client en supprimant le token.
    """
    return LogoutResponse(
        message=f"Utilisateur {current_user.username} déconnecté avec succès",
        timestamp=datetime.utcnow()
    )

@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(current_user: UserInfo = Depends(get_current_user)):
    """
    Renouveler le token d'authentification

    Génère un nouveau token pour l'utilisateur connecté.
    """
    # Récupérer les données utilisateur
    try:
        if hasattr(AuthService, 'get_user_by_username'):
            user_data = AuthService.get_user_by_username(current_user.username)
        else:
            user_data = AuthService.get_user(current_user.username)

        if not user_data:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    except Exception:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    # Créer le nouveau token
    if hasattr(user_data, 'username'):  # SQLAlchemy
        new_token = AuthService.create_access_token(user_data)
        full_name = f"{getattr(user_data, 'first_name', '') or ''} {getattr(user_data, 'last_name', '') or ''}".strip()
        if not full_name:
            full_name = user_data.username

        user_info = {
            "username": user_data.username,
            "is_admin": user_data.is_admin,
            "uuid": getattr(user_data, 'uuid', f"uuid-{user_data.username}"),
            "full_name": full_name
        }
    else:  # Dictionary
        new_token = AuthService.create_access_token(user_data, current_user.username)
        full_name = f"{user_data.get('first_name', '') or ''} {user_data.get('last_name', '') or ''}".strip()
        if not full_name:
            full_name = current_user.username

        user_info = {
            "username": current_user.username,
            "is_admin": user_data["is_admin"],
            "uuid": user_data.get("uuid", f"uuid-{current_user.username}"),
            "full_name": full_name
        }

    return LoginResponse(
        token=new_token,
        token_type="bearer",
        expires_in=AuthService.get_token_expire_time(),
        user=user_info
    )

@router.put("/password", response_model=dict)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Changer le mot de passe de l'utilisateur connecté
    """
    # Version simple (sans PostgreSQL)
    if hasattr(AuthService, 'verify_password') and not hasattr(AuthService, 'get_user_by_username'):
        if not AuthService.verify_password(current_user.username, password_data.current_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mot de passe actuel incorrect"
            )

        if not AuthService.update_password(current_user.username, password_data.new_password):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la mise à jour du mot de passe"
            )
    else:
        # Version PostgreSQL - nécessiterait l'implémentation complète
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Changement de mot de passe non implémenté pour cette version"
        )

    return {
        "message": "Mot de passe modifié avec succès",
        "timestamp": datetime.utcnow()
    }

@router.get("/users", response_model=dict)
async def list_users(admin_user: UserInfo = Depends(get_admin_user)):
    """
    Lister tous les utilisateurs (admin seulement)
    """
    users = AuthService.list_users()
    return {
        "users": users,
        "total_users": len(users),
        "timestamp": datetime.utcnow()
    }

@router.post("/users", response_model=dict)
async def create_user(
    user_data: CreateUserRequest,
    admin_user: UserInfo = Depends(get_admin_user)
):
    """
    Créer un nouvel utilisateur (admin seulement)
    """
    success = AuthService.create_user(user_data.username, user_data.password, user_data.is_admin)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'utilisateur existe déjà"
        )

    return {
        "message": f"Utilisateur '{user_data.username}' créé avec succès",
        "username": user_data.username,
        "is_admin": user_data.is_admin,
        "created_by": admin_user.username,
        "timestamp": datetime.utcnow()
    }

@router.get("/status", response_model=dict)
async def auth_status():
    """
    Statut du service d'authentification
    """
    try:
        total_users = len(getattr(AuthService, 'USERS_DB', {}))
        storage_type = "memory" if hasattr(AuthService, 'USERS_DB') else "database"
    except Exception:
        total_users = 0
        storage_type = "unknown"

    return {
        "service": "authentication",
        "status": "active",
        "storage": storage_type,
        "token_expiry_minutes": AuthService.get_token_expire_time() // 60,
        "total_users": total_users,
        "timestamp": datetime.utcnow()
    }