"""Configuration de la base de données PostgreSQL"""

import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData, text

# Charger les variables d'environnement depuis .env
load_dotenv()

# Configuration de la base de données
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("⚠️ DATABASE_URL non trouvé dans .env, utilisation de la valeur par défaut")
    DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/vps_manager"

print(f"🔗 Connexion à: {DATABASE_URL}")

# Création du moteur asyncio
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Mettre True pour debug SQL
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=300
)

# Session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base pour les modèles SQLAlchemy
Base = declarative_base()
metadata = MetaData()

# Dépendance pour obtenir une session DB
async def get_database_session() -> AsyncSession:
    """Obtenir une session de base de données"""
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Fonctions utilitaires
async def create_tables():
    """Créer toutes les tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_tables():
    """Supprimer toutes les tables (ATTENTION!)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Test de connexion
async def test_connection():
    """Tester la connexion à la base de données"""
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"Erreur de connexion DB: {e}")
        return False