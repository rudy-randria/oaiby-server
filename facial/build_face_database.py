#!/usr/bin/env python3
"""
Script pour créer une base de données de reconnaissance faciale
Support de plusieurs images par personne
Fichier: build_face_database.py
"""

import os
import json
from pathlib import Path
from datetime import datetime
from deepface import DeepFace
import shutil

# Configuration
IMAGES_SOURCE_DIR = "images"  # Dossier source avec sous-dossiers par personne
FACE_DATABASE_DIR = "face_database"  # Base de données DeepFace
USERS_DB_FILE = "users_database.json"  # Métadonnées des utilisateurs


def create_directories():
    """Créer les dossiers nécessaires"""
    Path(IMAGES_SOURCE_DIR).mkdir(exist_ok=True)
    Path(FACE_DATABASE_DIR).mkdir(exist_ok=True)
    print(f"✅ Dossiers créés:")
    print(f"   - {IMAGES_SOURCE_DIR} (mettez vos images ici)")
    print(f"   - {FACE_DATABASE_DIR} (base de données)")


def load_users_db():
    """Charger la base de données des utilisateurs"""
    if os.path.exists(USERS_DB_FILE):
        with open(USERS_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_users_db(users_db):
    """Sauvegarder la base de données des utilisateurs"""
    with open(USERS_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_db, f, indent=4, ensure_ascii=False)
    print(f"💾 Base de données sauvegardée: {USERS_DB_FILE}")


def get_image_files(folder_path):
    """Récupérer tous les fichiers images d'un dossier"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
    image_files = []

    for file in os.listdir(folder_path):
        if Path(file).suffix.lower() in image_extensions:
            image_files.append(os.path.join(folder_path, file))

    return image_files


def add_user_from_folder(user_id, username, email, full_name, folder_path):
    """
    Ajouter un utilisateur avec toutes ses images depuis un dossier

    Args:
        user_id (int): ID unique de l'utilisateur
        username (str): Nom d'utilisateur
        email (str): Email
        full_name (str): Nom complet
        folder_path (str): Chemin vers le dossier contenant les images
    """

    # Vérifier que le dossier existe
    if not os.path.exists(folder_path):
        print(f"❌ Erreur: Le dossier {folder_path} n'existe pas")
        return False

    # Récupérer toutes les images du dossier
    image_files = get_image_files(folder_path)

    if not image_files:
        print(f"❌ Aucune image trouvée dans {folder_path}")
        return False

    print(f"\n👤 Traitement de {full_name} ({username})")
    print(f"   📁 Dossier: {folder_path}")
    print(f"   📸 {len(image_files)} image(s) trouvée(s)")

    # Charger la base de données
    users_db = load_users_db()

    # Vérifier si l'utilisateur existe déjà
    if str(user_id) in users_db:
        print(f"   ⚠️  L'utilisateur ID {user_id} existe déjà")
        return False

    # Créer le dossier utilisateur dans la base de données
    user_db_folder = os.path.join(FACE_DATABASE_DIR, f"user_{user_id}")
    Path(user_db_folder).mkdir(exist_ok=True)

    valid_images = []

    # Traiter chaque image
    for idx, image_path in enumerate(image_files, 1):
        try:
            print(f"   🔍 Image {idx}/{len(image_files)}: {os.path.basename(image_path)}...", end=" ")

            # Vérifier que le visage est détectable
            faces = DeepFace.extract_faces(
                img_path=image_path,
                detector_backend='opencv',
                enforce_detection=True
            )

            if len(faces) == 0:
                print("❌ Aucun visage détecté")
                continue

            if len(faces) > 1:
                print("⚠️  Plusieurs visages détectés, ignoré")
                continue

            # Copier l'image dans le dossier utilisateur
            destination_path = os.path.join(
                user_db_folder,
                f"{username}_{idx}.jpg"
            )
            shutil.copy(image_path, destination_path)
            valid_images.append(destination_path)

            print(f"✅ OK")

        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            continue

    # Vérifier qu'au moins une image est valide
    if not valid_images:
        print(f"   ❌ Aucune image valide pour {username}")
        # Supprimer le dossier créé
        if os.path.exists(user_db_folder):
            shutil.rmtree(user_db_folder)
        return False

    # Ajouter à la base de données
    users_db[str(user_id)] = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "full_name": full_name,
        "face_images": valid_images,
        "image_count": len(valid_images),
        "registered_at": datetime.utcnow().isoformat()
    }

    # Sauvegarder
    save_users_db(users_db)
    print(f"   ✅ {len(valid_images)} image(s) ajoutée(s) avec succès!\n")
    return True


def scan_images_folder():
    """Scanner automatiquement le dossier images/ et ajouter tous les utilisateurs"""

    if not os.path.exists(IMAGES_SOURCE_DIR):
        print(f"❌ Le dossier {IMAGES_SOURCE_DIR} n'existe pas")
        return

    # Lister tous les sous-dossiers
    subfolders = [f for f in os.listdir(IMAGES_SOURCE_DIR)
                  if os.path.isdir(os.path.join(IMAGES_SOURCE_DIR, f))]

    if not subfolders:
        print(f"❌ Aucun sous-dossier trouvé dans {IMAGES_SOURCE_DIR}")
        print(f"\n💡 Structure attendue:")
        print(f"   images/")
        print(f"   ├── john_doe/")
        print(f"   │   ├── photo1.jpg")
        print(f"   │   ├── photo2.jpg")
        print(f"   │   └── photo3.jpg")
        print(f"   ├── jane_smith/")
        print(f"   │   └── photo1.jpg")
        return

    print(f"\n📂 {len(subfolders)} dossier(s) trouvé(s):")
    for folder in subfolders:
        print(f"   - {folder}")

    print("\n" + "=" * 80)
    print("🚀 DÉBUT DE L'IMPORTATION")
    print("=" * 80)

    users_db = load_users_db()
    next_user_id = max([int(uid) for uid in users_db.keys()], default=0) + 1

    for folder_name in subfolders:
        folder_path = os.path.join(IMAGES_SOURCE_DIR, folder_name)

        # Générer les informations utilisateur depuis le nom du dossier
        username = folder_name
        email = f"{folder_name}@example.com"
        full_name = folder_name.replace('_', ' ').title()

        add_user_from_folder(
            user_id=next_user_id,
            username=username,
            email=email,
            full_name=full_name,
            folder_path=folder_path
        )

        next_user_id += 1


def list_users():
    """Lister tous les utilisateurs de la base de données"""
    users_db = load_users_db()

    if not users_db:
        print("📭 La base de données est vide")
        return

    print(f"\n{'=' * 80}")
    print(f"👥 UTILISATEURS ENREGISTRÉS ({len(users_db)})")
    print(f"{'=' * 80}")

    for user_id, user_data in users_db.items():
        print(f"\n🆔 ID: {user_data['user_id']}")
        print(f"   👤 Nom: {user_data['full_name']}")
        print(f"   📧 Email: {user_data['email']}")
        print(f"   🔑 Username: {user_data['username']}")
        print(f"   📸 Images: {user_data['image_count']}")
        print(f"   📅 Enregistré: {user_data['registered_at']}")


def test_recognition(test_image_path):
    """
    Tester la reconnaissance faciale avec une image

    Args:
        test_image_path (str): Chemin vers l'image de test
    """

    if not os.path.exists(test_image_path):
        print(f"❌ L'image de test {test_image_path} n'existe pas")
        return

    users_db = load_users_db()

    if not users_db:
        print("❌ La base de données est vide")
        return

    try:
        print(f"\n{'=' * 80}")
        print(f"🔍 TEST DE RECONNAISSANCE")
        print(f"{'=' * 80}")
        print(f"📷 Image de test: {test_image_path}\n")

        # Rechercher le visage dans la base de données
        result = DeepFace.find(
            img_path=test_image_path,
            db_path=FACE_DATABASE_DIR,
            model_name='VGG-Face',
            detector_backend='opencv',
            distance_metric='cosine',
            enforce_detection=True,
            silent=True
        )

        if len(result) > 0 and not result[0].empty:
            matched_image_path = result[0].iloc[0]['identity']
            distance = result[0].iloc[0]['distance']
            confidence = (1 - distance) * 100

            # Trouver l'utilisateur correspondant
            for user_id, user_data in users_db.items():
                if any(img_path in matched_image_path for img_path in user_data['face_images']):
                    print(f"✅ VISAGE RECONNU!")
                    print(f"   👤 Utilisateur: {user_data['full_name']}")
                    print(f"   🔑 Username: {user_data['username']}")
                    print(f"   📧 Email: {user_data['email']}")
                    print(f"   📊 Confiance: {confidence:.2f}%")
                    print(f"   📏 Distance: {distance:.4f}")
                    print(f"   🖼️  Image correspondante: {os.path.basename(matched_image_path)}")
                    break
        else:
            print("❌ VISAGE NON RECONNU")
            print("   Aucune correspondance trouvée dans la base de données")

    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")


def main():
    """Fonction principale"""

    print("=" * 80)
    print("🎭 CONSTRUCTION DE LA BASE DE DONNÉES DE RECONNAISSANCE FACIALE")
    print("=" * 80)
    print()

    # Créer les dossiers
    create_directories()
    print()

    # Scanner et importer automatiquement depuis le dossier images/
    scan_images_folder()

    # Lister les utilisateurs
    list_users()

    # Test de reconnaissance (optionnel)
    # Décommente et remplace par une vraie image de test
    # test_recognition("test_image.jpg")


if __name__ == "__main__":
    main()