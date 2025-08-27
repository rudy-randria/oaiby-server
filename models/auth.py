"""Modèles Pydantic pour l'authentification - Version simplifiée"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    """Modèle pour la requête de connexion"""
    username: str
    password: str

class LoginResponse(BaseModel):
    """Modèle pour la réponse de connexion"""
    token: str
    token_type: str = "bearer"
    expires_in: int
    user: Optional[dict] = None

class UserInfo(BaseModel):
    """Modèle pour les informations utilisateur"""
    username: str
    is_admin: bool = False
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

class TokenData(BaseModel):
    """Modèle pour les données contenues dans le token"""
    username: Optional[str] = None
    is_admin: bool = False
    expires_at: Optional[datetime] = None

class LogoutResponse(BaseModel):
    """Modèle pour la réponse de déconnexion"""
    message: str
    timestamp: datetime

class ErrorResponse(BaseModel):
    """Modèle pour les réponses d'erreur d'authentification"""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime

class CreateUserRequest(BaseModel):
    """Modèle pour créer un nouvel utilisateur"""
    username: str
    password: str
    is_admin: bool = False

class UpdateUserRequest(BaseModel):
    """Modèle pour mettre à jour un utilisateur"""
    password: Optional[str] = None
    is_admin: Optional[bool] = None

class ChangePasswordRequest(BaseModel):
    """Modèle pour changer le mot de passe"""
    current_password: str
    new_password: str