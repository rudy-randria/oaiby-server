"""Service d'authentification pour l'API VPS Manager avec PostgreSQL"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from models.auth import UserInfo, TokenData
from models.database.user import User
from config.database import get_database_session

# Configuration JWT (À CHANGER EN PRODUCTION!)
SECRET_KEY = "votre-clé-secrète-ultra-sécurisée-changez-moi-en-production-postgresql"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

class AuthService:
    """Service pour gérer l'authentification avec PostgreSQL"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hasher un mot de passe avec bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Vérifier un mot de passe hashé"""
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False

    @staticmethod
    async def get_user_by_username(
        username: str,
        db: AsyncSession
    ) -> Optional[User]:
        """Obtenir un utilisateur par nom d'utilisateur"""
        result = await db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(
        user_id: int,
        db: AsyncSession
    ) -> Optional[User]:
        """Obtenir un utilisateur par ID"""
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def create_access_token(user: User) -> str:
        """Créer un token JWT"""
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {
            "sub": str(user.id),  # Subject = user ID
            "username": user.username,
            "is_admin": user.is_admin,
            "is_superuser": user.is_superuser,
            "uuid": user.uuid,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    async def verify_token(
        token: str,
        db: AsyncSession = Depends(get_database_session)
    ) -> UserInfo:
        """Vérifier et décoder un token JWT"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            username: str = payload.get("username")

            if user_id is None or username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token invalide - données manquantes",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Vérifier que l'utilisateur existe encore et est actif
            user = await AuthService.get_user_by_id(int(user_id), db)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Utilisateur introuvable ou inactif",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return UserInfo(
                username=user.username,
                is_admin=user.is_admin,
                created_at=user.created_at,
                last_login=user.last_login
            )

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expiré",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token invalide: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Format de token invalide",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    async def authenticate_user(
        username: str,
        password: str,
        db: AsyncSession,
        client_ip: str = None
    ) -> Optional[User]:
        """Authentifier un utilisateur avec gestion des tentatives"""

        # Récupérer l'utilisateur
        user = await AuthService.get_user_by_username(username, db)
        if not user:
            return None

        # Vérifier si le compte est verrouillé
        if user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Compte verrouillé jusqu'à {user.locked_until}"
            )

        # Vérifier si le compte est actif
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Compte désactivé"
            )

        # Vérifier le mot de passe
        if not AuthService.verify_password(password, user.password_hash):
            # Incrémenter les tentatives de connexion échouées
            await AuthService._handle_failed_login(user, db)
            return None

        # Connexion réussie - réinitialiser les tentatives et mettre à jour
        await AuthService._handle_successful_login(user, db, client_ip)
        return user

    @staticmethod
    async def _handle_failed_login(user: User, db: AsyncSession):
        """Gérer les tentatives de connexion échouées"""
        user.login_attempts += 1

        if user.login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)

        await db.commit()

    @staticmethod
    async def _handle_successful_login(user: User, db: AsyncSession, client_ip: str = None):
        """Gérer une connexion réussie"""
        user.last_login = datetime.utcnow()
        user.login_attempts = 0
        user.locked_until = None
        if client_ip:
            user.last_ip = client_ip

        await db.commit()

    @staticmethod
    async def create_user(
        username: str,
        password: str,
        email: str = None,
        is_admin: bool = False,
        first_name: str = None,
        last_name: str = None,
        db: AsyncSession = None
    ) -> User:
        """Créer un nouvel utilisateur"""
        try:
            hashed_password = AuthService.hash_password(password)

            new_user = User(
                username=username,
                email=email,
                password_hash=hashed_password,
                is_admin=is_admin,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )

            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)

            return new_user

        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nom d'utilisateur ou email déjà utilisé"
            )

    @staticmethod
    async def update_password(
        user_id: int,
        new_password: str,
        db: AsyncSession
    ) -> bool:
        """Mettre à jour le mot de passe d'un utilisateur"""
        hashed_password = AuthService.hash_password(new_password)

        result = await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                password_hash=hashed_password,
                password_changed_at=datetime.utcnow()
            )
        )

        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def deactivate_user(user_id: int, db: AsyncSession) -> bool:
        """Désactiver un utilisateur"""
        result = await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )

        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def list_users(db: AsyncSession, skip: int = 0, limit: int = 100):
        """Lister tous les utilisateurs"""
        result = await db.execute(
            select(User)
            .offset(skip)
            .limit(limit)
            .order_by(User.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def init_default_admin(db: AsyncSession):
        """Créer l'utilisateur admin par défaut s'il n'existe pas"""
        admin_user = await AuthService.get_user_by_username("admin", db)

        if not admin_user:
            print("🔧 Création de l'utilisateur admin par défaut...")
            await AuthService.create_user(
                username="admin",
                password="password",
                email="admin@vpsmanager.local",
                is_admin=True,
                first_name="Administrator",
                last_name="System",
                db=db
            )
            print("✅ Utilisateur admin créé avec succès")
        else:
            print("✅ Utilisateur admin existe déjà")

    @staticmethod
    def get_token_expire_time() -> int:
        """Obtenir le temps d'expiration des tokens en secondes"""
        return ACCESS_TOKEN_EXPIRE_MINUTES * 60