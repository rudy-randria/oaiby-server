from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets
import hashlib
import re
import ipaddress
from pydantic import BaseModel
from core.config import settings
import time
import logging

logger = logging.getLogger("vps_manager.security")

# Configuration de hachage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuration JWT
ALGORITHM = "HS256"
security = HTTPBearer()

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    username: Optional[str] = None
    permissions: List[str] = []

class User(BaseModel):
    username: str
    email: Optional[str] = None
    permissions: List[str] = []
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    permissions: List[str] = []

class RateLimitInfo(BaseModel):
    requests: int
    window_start: float
    blocked_until: Optional[float] = None

# Stockage en mémoire pour la démo (en production, utiliser Redis/DB)
users_db: Dict[str, Dict] = {}
rate_limits: Dict[str, RateLimitInfo] = {}
api_keys: Dict[str, Dict] = {}

class SecurityManager:
    """Gestionnaire de sécurité centralisé"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Vérifier un mot de passe"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hacher un mot de passe"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Créer un token JWT"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> TokenData:
        """Vérifier et décoder un token JWT"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            permissions: List[str] = payload.get("permissions", [])
            
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token invalide",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return TokenData(username=username, permissions=permissions)
        
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def create_user(user_data: UserCreate) -> User:
        """Créer un nouvel utilisateur"""
        if user_data.username in users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nom d'utilisateur déjà existant"
            )
        
        # Valider le mot de passe
        SecurityManager.validate_password(user_data.password)
        
        hashed_password = SecurityManager.get_password_hash(user_data.password)
        
        user = User(
            username=user_data.username,
            email=user_data.email,
            permissions=user_data.permissions,
            created_at=datetime.utcnow()
        )
        
        users_db[user_data.username] = {
            "user": user.dict(),
            "hashed_password": hashed_password
        }
        
        logger.info(f"Utilisateur créé: {user_data.username}")
        return user
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        """Authentifier un utilisateur"""
        user_data = users_db.get(username)
        if not user_data:
            return None
        
        if not SecurityManager.verify_password(password, user_data["hashed_password"]):
            return None
        
        user = User(**user_data["user"])
        
        # Mettre à jour la dernière connexion
        user.last_login = datetime.utcnow()
        users_db[username]["user"]["last_login"] = user.last_login.isoformat()
        
        return user
    
    @staticmethod
    def validate_password(password: str) -> bool:
        """Valider la force d'un mot de passe"""
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le mot de passe doit contenir au moins 8 caractères"
            )
        
        if not re.search(r"[A-Z]", password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le mot de passe doit contenir au moins une majuscule"
            )
        
        if not re.search(r"[a-z]", password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le mot de passe doit contenir au moins une minuscule"
            )
        
        if not re.search(r"\d", password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le mot de passe doit contenir au moins un chiffre"
            )
        
        return True
    
    @staticmethod
    def validate_command(command: str) -> bool:
        """Valider qu'une commande est autorisée"""
        if not command or len(command.strip()) == 0:
            return False
        
        # Première partie de la commande
        cmd_parts = command.strip().split()
        base_command = cmd_parts[0]
        
        # Vérifier si la commande est dans la liste autorisée
        if base_command not in settings.ALLOWED_COMMANDS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Commande non autorisée: {base_command}"
            )
        
        # Vérifier les caractères dangereux
        dangerous_chars = [';', '&', '|', '$(', '`', '>>', '&&', '||']
        if any(char in command for char in dangerous_chars):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Caractères dangereux détectés dans la commande"
            )
        
        # Vérifier les commandes dangereuses
        dangerous_commands = ['rm -rf', 'mkfs', 'dd if=', 'sudo su', 'chmod 777']
        if any(dangerous in command.lower() for dangerous in dangerous_commands):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Commande potentiellement dangereuse détectée"
            )
        
        return True

class RateLimiter:
    """Limiteur de débit des requêtes"""
    
    @staticmethod
    def is_rate_limited(identifier: str, max_requests: int = 100, window_seconds: int = 3600) -> bool:
        """Vérifier si un identifiant est limité en débit"""
        current_time = time.time()
        
        if identifier not in rate_limits:
            rate_limits[identifier] = RateLimitInfo(
                requests=1,
                window_start=current_time
            )
            return False
        
        rate_info = rate_limits[identifier]
        
        # Vérifier si on est dans une période de blocage
        if rate_info.blocked_until and current_time < rate_info.blocked_until:
            return True
        
        # Réinitialiser la fenêtre si nécessaire
        if current_time - rate_info.window_start > window_seconds:
            rate_info.requests = 1
            rate_info.window_start = current_time
            rate_info.blocked_until = None
            return False
        
        # Incrémenter le compteur
        rate_info.requests += 1
        
        # Vérifier la limite
        if rate_info.requests > max_requests:
            # Bloquer pour le reste de la fenêtre + 30 minutes de pénalité
            rate_info.blocked_until = current_time + 1800  # 30 minutes
            logger.warning(f"Rate limit dépassé pour {identifier}")
            return True
        
        return False

class APIKeyManager:
    """Gestionnaire de clés API"""
    
    @staticmethod
    def create_api_key(name: str, permissions: List[str], expires_days: Optional[int] = None) -> str:
        """Créer une nouvelle clé API"""
        api_key = f"vps_{secrets.token_urlsafe(32)}"
        
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        api_keys[api_key] = {
            "name": name,
            "permissions": permissions,
            "created_at": datetime.utcnow(),
            "expires_at": expires_at,
            "last_used": None,
            "usage_count": 0
        }
        
        logger.info(f"Clé API créée: {name}")
        return api_key
    
    @staticmethod
    def validate_api_key(api_key: str) -> Optional[Dict]:
        """Valider une clé API"""
        if api_key not in api_keys:
            return None
        
        key_info = api_keys[api_key]
        
        # Vérifier l'expiration
        if key_info["expires_at"] and datetime.utcnow() > key_info["expires_at"]:
            return None
        
        # Mettre à jour l'utilisation
        key_info["last_used"] = datetime.utcnow()
        key_info["usage_count"] += 1
        
        return key_info

def get_client_ip(request: Request) -> str:
    """Récupérer l'IP du client"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host

def validate_ip_whitelist(ip: str, whitelist: List[str]) -> bool:
    """Valider qu'une IP est dans la whitelist"""
    if not whitelist:
        return True
    
    try:
        client_ip = ipaddress.ip_address(ip)
        
        for allowed in whitelist:
            if "/" in allowed:  # CIDR notation
                if client_ip in ipaddress.ip_network(allowed, strict=False):
                    return True
            else:  # IP exacte
                if client_ip == ipaddress.ip_address(allowed):
                    return True
        
        return False
    except ValueError:
        return False

# Dépendances FastAPI pour l'authentification
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Récupérer l'utilisateur actuel depuis le token"""
    token_data = SecurityManager.verify_token(credentials.credentials)
    
    user_data = users_db.get(token_data.username)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur non trouvé"
        )
    
    return User(**user_data["user"])

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Vérifier que l'utilisateur est actif"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Utilisateur inactif"
        )
    return current_user

def require_permission(permission: str):
    """Décorateur pour exiger une permission spécifique"""
    def permission_checker(current_user: User = Depends(get_current_active_user)):
        if permission not in current_user.permissions and "admin" not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission requise: {permission}"
            )
        return current_user
    return permission_checker

def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    """Décorateur pour limiter le débit des requêtes"""
    def rate_limit_checker(request: Request):
        client_ip = get_client_ip(request)
        
        if RateLimiter.is_rate_limited(client_ip, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de requêtes, réessayez plus tard"
            )
        
        return True
    return Depends(rate_limit_checker)

# Initialisation des utilisateurs par défaut
def init_default_users():
    """Initialiser les utilisateurs par défaut"""
    if not users_db:
        # Créer un admin par défaut
        default_admin = UserCreate(
            username="admin",
            password="ChangeMe123!",
            email="admin@localhost",
            permissions=["admin", "system", "hardware", "network", "services"]
        )
        
        try:
            SecurityManager.create_user(default_admin)
            logger.info("Utilisateur admin par défaut créé (mot de passe: ChangeMe123!)")
        except HTTPException:
            pass  # L'utilisateur existe déjà
        
        # Créer une clé API par défaut
        default_api_key = APIKeyManager.create_api_key(
            name="default-api-key",
            permissions=["read"],
            expires_days=365
        )
        logger.info(f"Clé API par défaut créée: {default_api_key}")

# Middleware de sécurité personnalisé
class SecurityMiddleware:
    """Middleware de sécurité pour les en-têtes"""
    
    @staticmethod
    def add_security_headers(response):
        """Ajouter les en-têtes de sécurité"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response