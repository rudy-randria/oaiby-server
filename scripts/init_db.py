#!/usr/bin/env python3
"""Script d'initialisation de la base de données PostgreSQL"""

import asyncio
import sys
from pathlib import Path

# Ajouter le dossier racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import create_tables, test_connection, async_session
from services.auth_service import AuthService
from models.database.user import User


async def init_database():
    """Initialiser la base de données"""

    print("🚀 Initialisation de la base de données PostgreSQL...")

    # 1. Test de connexion
    print("📡 Test de connexion à PostgreSQL...")
    if not await test_connection():
        print("❌ Impossible de se connecter à PostgreSQL")
        print("📋 Vérifiez que PostgreSQL est démarré et accessible")
        print("📋 URL de connexion par défaut: postgresql+asyncpg://postgres:password@localhost:5432/vps_manager")
        return False

    print("✅ Connexion PostgreSQL réussie")

    # 2. Création des tables
    print("📋 Création des tables...")
    try:
        await create_tables()
        print("✅ Tables créées avec succès")
    except Exception as e:
        print(f"❌ Erreur lors de la création des tables: {e}")
        return False

    # 3. Création de l'utilisateur admin
    print("👤 Création de l'utilisateur administrateur...")
    async with async_session() as db:
        try:
            await AuthService.init_default_admin(db)
            print("✅ Utilisateur admin initialisé")
        except Exception as e:
            print(f"❌ Erreur lors de la création de l'admin: {e}")
            return False

    print("\n🎉 Initialisation terminée avec succès!")
    print("\n📋 Informations de connexion:")
    print("   👤 Utilisateur: admin")
    print("   🔑 Mot de passe: password")
    print("   ⚠️  CHANGEZ CE MOT DE PASSE EN PRODUCTION!")
    print("\n🌐 Démarrez maintenant votre API:")
    print("   python main.py")

    return True


async def reset_database():
    """Réinitialiser complètement la base de données (ATTENTION!)"""
    print("⚠️  RÉINITIALISATION COMPLÈTE DE LA BASE DE DONNÉES")

    response = input("❓ Êtes-vous sûr? Cela supprimera TOUTES les données! (oui/non): ")
    if response.lower() != 'oui':
        print("🛑 Réinitialisation annulée")
        return

    print("🗑️  Suppression des tables existantes...")
    try:
        from config.database import drop_tables
        await drop_tables()
        print("✅ Tables supprimées")
    except Exception as e:
        print(f"⚠️  Erreur lors de la suppression: {e}")

    # Réinitialiser
    await init_database()


async def show_users():
    """Afficher tous les utilisateurs"""
    print("👥 Utilisateurs enregistrés:")

    async with async_session() as db:
        try:
            users = await AuthService.list_users(db)

            if not users:
                print("   Aucun utilisateur trouvé")
                return

            for user in users:
                status = "🟢 Actif" if user.is_active else "🔴 Inactif"
                admin = "👑 Admin" if user.is_admin else "👤 User"
                locked = " 🔒 Verrouillé" if user.is_locked else ""

                print(f"   • {user.username} ({user.email or 'pas d email'}) - {admin} - {status}{locked}")
                print(f"     └─ Créé: {user.created_at}, Dernière connexion: {user.last_login or 'Jamais'}")

        except Exception as e:
            print(f"❌ Erreur: {e}")


async def create_user_interactive():
    """Créer un utilisateur interactivement"""
    print("👤 Création d'un nouvel utilisateur")

    username = input("📝 Nom d'utilisateur: ").strip()
    if not username:
        print("❌ Le nom d'utilisateur ne peut pas être vide")
        return

    email = input("📧 Email (optionnel): ").strip() or None
    password = input("🔑 Mot de passe: ").strip()
    if not password:
        print("❌ Le mot de passe ne peut pas être vide")
        return

    is_admin = input("👑 Droits admin? (o/n): ").strip().lower() == 'o'
    first_name = input("📛 Prénom (optionnel): ").strip() or None
    last_name = input("📛 Nom (optionnel): ").strip() or None

    async with async_session() as db:
        try:
            user = await AuthService.create_user(
                username=username,
                password=password,
                email=email,
                is_admin=is_admin,
                first_name=first_name,
                last_name=last_name,
                db=db
            )

            print(f"✅ Utilisateur '{user.username}' créé avec succès!")

        except Exception as e:
            print(f"❌ Erreur lors de la création: {e}")


def print_help():
    """Afficher l'aide"""
    print("""
🛠️  Script d'administration de la base de données VPS Manager

Usage: python scripts/init_db.py [command]

Commandes disponibles:
  init        Initialiser la base de données (défaut)
  reset       Réinitialiser complètement la DB (DANGEREUX!)
  users       Afficher tous les utilisateurs
  create-user Créer un nouvel utilisateur
  help        Afficher cette aide

Exemples:
  python scripts/init_db.py
  python scripts/init_db.py reset  
  python scripts/init_db.py users
  python scripts/init_db.py create-user
""")


async def main():
    """Point d'entrée principal"""

    command = sys.argv[1] if len(sys.argv) > 1 else "init"

    if command == "help":
        print_help()
    elif command == "init":
        await init_database()
    elif command == "reset":
        await reset_database()
    elif command == "users":
        await show_users()
    elif command == "create-user":
        await create_user_interactive()
    else:
        print(f"❌ Commande inconnue: {command}")
        print("💡 Utilisez 'help' pour voir les commandes disponibles")


if __name__ == "__main__":
    asyncio.run(main())