"""Modèle SQLAlchemy pour les utilisateurs"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from config.database import Base
import uuid
from datetime import datetime

class User(Base):
    """Modèle utilisateur pour l'authentification"""

    __tablename__ = "users"

    # Clé primaire
    id = Column(Integer, primary_key=True, index=True)

    # Identifiant unique
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))

    # Informations de connexion
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)

    # Permissions
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Métadonnées
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    phone = Column(String(20), nullable=True)

    # Dates
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Sessions et sécurité
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    # Métadonnées additionnelles
    notes = Column(Text, nullable=True)
    last_ip = Column(String(45), nullable=True)  # IPv6 compatible

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', is_admin={self.is_admin})>"

    def to_dict(self):
        """Convertir en dictionnaire (sans mot de passe)"""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "is_superuser": self.is_superuser,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login,
            "password_changed_at": self.password_changed_at,
            "login_attempts": self.login_attempts,
            "locked_until": self.locked_until,
            "notes": self.notes,
            "last_ip": self.last_ip
        }

    @property
    def full_name(self):
        """Nom complet de l'utilisateur"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.username

    @property
    def is_locked(self):
        """Vérifier si le compte est verrouillé"""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False