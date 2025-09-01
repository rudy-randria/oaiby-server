"""Routes d'authentification pour l'API VPS Manager"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
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

# Import du service d'authentification PostgreSQL
from services.auth_service import AuthService
from config.database import get_database_session

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

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_database_session)
) -> UserInfo:
    """Dépendance pour obtenir l'utilisateur actuel depuis le token"""
    return await AuthService.verify_token(credentials.credentials, db)

async def get_admin_user(current_user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """Dépendance pour vérifier que l'utilisateur est admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits administrateur requis"
        )
    return current_user

@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_database_session)
):
    """
    Connexion utilisateur

    Authentifie un utilisateur et retourne un token JWT.

    **Compte de test:**
    - `admin` / `password` (administrateur)
    """
    # Obtenir l'IP du client
    client_ip = request.client.host if request.client else None

    user = await AuthService.authenticate_user(
        login_data.username,
        login_data.password,
        db,
        client_ip
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect"
        )

    # Créer le token
    token = AuthService.create_access_token(user)

    # Préparer les informations utilisateur
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    if not full_name:
        full_name = user.username

    user_data = {
        "username": user.username,
        "is_admin": user.is_admin,
        "uuid": user.uuid,
        "full_name": full_name
    }

    return LoginResponse(
        token=token,
        token_type="bearer",
        expires_in=AuthService.get_token_expire_time(),
        user=user_data
    )

@router.get("/me", response_model=dict)
async def get_current_user_info(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_database_session)
):
    """
    Obtenir les informations de l'utilisateur connecté

    Retourne les informations détaillées de l'utilisateur authentifié.
    """
    # Récupérer les données complètes de l'utilisateur
    user_data = await AuthService.get_user_by_username(current_user.username, db)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable"
        )

    # Retourner les informations sans les données sensibles
    return {
        "id": user_data.id,
        "username": user_data.username,
        "email": user_data.email,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "is_admin": user_data.is_admin,
        "is_superuser": user_data.is_superuser,
        "is_active": user_data.is_active,
        "created_at": user_data.created_at,
        "last_login": user_data.last_login,
        "last_ip": user_data.last_ip,
        "uuid": user_data.uuid
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
async def refresh_token(
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_database_session)
):
    """
    Renouveler le token d'authentification

    Génère un nouveau token pour l'utilisateur connecté.
    """
    # Récupérer les données utilisateur complètes
    user_data = await AuthService.get_user_by_username(current_user.username, db)

    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable"
        )

    # Créer le nouveau token
    new_token = AuthService.create_access_token(user_data)

    # Préparer les informations utilisateur
    full_name = f"{user_data.first_name or ''} {user_data.last_name or ''}".strip()
    if not full_name:
        full_name = user_data.username

    user_info = {
        "username": user_data.username,
        "is_admin": user_data.is_admin,
        "uuid": user_data.uuid,
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
    current_user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_database_session)
):
    """
    Changer le mot de passe de l'utilisateur connecté
    """
    # Récupérer l'utilisateur complet pour vérifier l'ancien mot de passe
    user = await AuthService.get_user_by_username(current_user.username, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable"
        )

    # Vérifier l'ancien mot de passe
    if not AuthService.verify_password(password_data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect"
        )

    # Mettre à jour le mot de passe
    success = await AuthService.update_password(user.id, password_data.new_password, db)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour du mot de passe"
        )

    return {
        "message": "Mot de passe modifié avec succès",
        "timestamp": datetime.utcnow()
    }

@router.get("/users", response_model=dict)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: UserInfo = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database_session)
):
    """
    Lister tous les utilisateurs (admin seulement)
    """
    users = await AuthService.list_users(db, skip, limit)

    # Convertir en dictionnaire et exclure les mots de passe
    users_data = []
    for user in users:
        user_dict = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_admin": user.is_admin,
            "is_superuser": user.is_superuser,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "uuid": user.uuid
        }
        users_data.append(user_dict)

    return {
        "users": users_data,
        "total_users": len(users_data),
        "skip": skip,
        "limit": limit,
        "timestamp": datetime.utcnow()
    }

@router.post("/users", response_model=dict)
async def create_user(
    user_data: CreateUserRequest,
    admin_user: UserInfo = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database_session)
):
    """
    Créer un nouvel utilisateur (admin seulement)
    """
    try:
        new_user = await AuthService.create_user(
            username=user_data.username,
            password=user_data.password,
            email=getattr(user_data, 'email', None),
            is_admin=user_data.is_admin,
            first_name=getattr(user_data, 'first_name', None),
            last_name=getattr(user_data, 'last_name', None),
            db=db
        )

        return {
            "message": f"Utilisateur '{user_data.username}' créé avec succès",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "is_admin": new_user.is_admin,
                "uuid": new_user.uuid
            },
            "created_by": admin_user.username,
            "timestamp": datetime.utcnow()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création de l'utilisateur: {str(e)}"
        )

@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: int,
    admin_user: UserInfo = Depends(get_admin_user),
    db: AsyncSession = Depends(get_database_session)
):
    """
    Désactiver un utilisateur (admin seulement)
    """
    success = await AuthService.deactivate_user(user_id, db)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable"
        )

    return {
        "message": f"Utilisateur avec l'ID {user_id} désactivé avec succès",
        "deactivated_by": admin_user.username,
        "timestamp": datetime.utcnow()
    }

@router.get("/status", response_model=dict)
async def auth_status(db: AsyncSession = Depends(get_database_session)):
    """
    Statut du service d'authentification
    """
    try:
        users = await AuthService.list_users(db, 0, 1000)  # Limite élevée pour compter
        total_users = len(users)
    except Exception:
        total_users = 0

    return {
        "service": "authentication",
        "status": "active",
        "storage": "postgresql",
        "token_expiry_minutes": AuthService.get_token_expire_time() // 60,
        "total_users": total_users,
        "timestamp": datetime.utcnow()
    }

@router.post("/init-admin")
async def initialize_admin(db: AsyncSession = Depends(get_database_session)):
    """
    Initialiser l'utilisateur admin par défaut
    """
    try:
        await AuthService.init_default_admin(db)
        return {
            "message": "Initialisation de l'admin terminée",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'initialisation: {str(e)}"
        )