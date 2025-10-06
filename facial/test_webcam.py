#!/usr/bin/env python3
"""
Test de reconnaissance faciale en temps réel via webcam
Fichier: test_webcam.py
"""

import cv2
import os
import json
from deepface import DeepFace
from datetime import datetime
import numpy as np

# Configuration
FACE_DATABASE_DIR = "face_database"
USERS_DB_FILE = "users_database.json"
TEMP_TEST_IMAGE = "temp_webcam_test.jpg"

# Couleurs (BGR)
COLOR_GREEN = (0, 255, 0)
COLOR_RED = (0, 0, 255)
COLOR_BLUE = (255, 0, 0)
COLOR_WHITE = (255, 255, 255)


def load_users_db():
    """Charger la base de données des utilisateurs"""
    if os.path.exists(USERS_DB_FILE):
        with open(USERS_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def recognize_face(frame):
    """
    Reconnaître un visage dans une frame

    Args:
        frame: Image capturée de la webcam (numpy array)

    Returns:
        dict: Résultat de la reconnaissance ou None
    """
    try:
        # Sauvegarder temporairement la frame
        cv2.imwrite(TEMP_TEST_IMAGE, frame)

        # Rechercher dans la base de données
        result = DeepFace.find(
            img_path=TEMP_TEST_IMAGE,
            db_path=FACE_DATABASE_DIR,
            model_name='VGG-Face',
            detector_backend='opencv',
            distance_metric='cosine',
            enforce_detection=False,
            silent=True
        )

        # Supprimer l'image temporaire
        if os.path.exists(TEMP_TEST_IMAGE):
            os.remove(TEMP_TEST_IMAGE)

        if len(result) > 0 and not result[0].empty:
            matched_image_path = result[0].iloc[0]['identity']
            distance = result[0].iloc[0]['distance']
            confidence = (1 - distance) * 100

            return {
                'matched_image': matched_image_path,
                'distance': distance,
                'confidence': confidence
            }

        return None

    except Exception as e:
        print(f"Erreur reconnaissance: {e}")
        return None


def find_user_from_image_path(users_db, image_path):
    """Trouver l'utilisateur correspondant à une image"""
    for user_id, user_data in users_db.items():
        if any(img in image_path for img in user_data['face_images']):
            return user_data
    return None


def draw_text_with_background(frame, text, position, font_scale=0.7, thickness=2):
    """Dessiner du texte avec un fond pour meilleure lisibilité"""
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Calculer la taille du texte
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)

    x, y = position

    # Dessiner le rectangle de fond
    cv2.rectangle(frame,
                  (x - 5, y - text_height - 5),
                  (x + text_width + 5, y + baseline + 5),
                  (0, 0, 0),
                  cv2.FILLED)

    # Dessiner le texte
    cv2.putText(frame, text, (x, y), font, font_scale, COLOR_WHITE, thickness)


def main():
    """Fonction principale"""

    print("=" * 80)
    print("🎥 TEST DE RECONNAISSANCE FACIALE PAR WEBCAM")
    print("=" * 80)
    print()

    # Vérifier la base de données
    if not os.path.exists(FACE_DATABASE_DIR):
        print("❌ La base de données n'existe pas!")
        print("   Exécutez d'abord: python build_face_database.py")
        return

    users_db = load_users_db()

    if not users_db:
        print("❌ Aucun utilisateur enregistré!")
        print("   Exécutez d'abord: python build_face_database.py")
        return

    print(f"✅ Base de données chargée: {len(users_db)} utilisateur(s)")
    print()

    # Liste des utilisateurs
    print("👥 Utilisateurs enregistrés:")
    for user_id, user_data in users_db.items():
        print(f"   - {user_data['full_name']} ({user_data['username']})")
    print()

    # Initialiser la webcam
    print("📹 Démarrage de la webcam...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Impossible d'ouvrir la webcam!")
        return

    print("✅ Webcam démarrée!")
    print()
    print("=" * 80)
    print("INSTRUCTIONS:")
    print("  • Appuyez sur ESPACE pour capturer et reconnaître")
    print("  • Appuyez sur 'R' pour reconnaissance continue (auto)")
    print("  • Appuyez sur 'Q' pour quitter")
    print("=" * 80)
    print()

    last_recognition = None
    auto_recognize = False
    frame_count = 0

    try:
        while True:
            # Lire la frame
            ret, frame = cap.read()

            if not ret:
                print("❌ Erreur de lecture de la webcam")
                break

            # Miroir horizontal (selfie mode)
            frame = cv2.flip(frame, 1)

            # Copie pour affichage
            display_frame = frame.copy()

            # Dessiner les instructions
            draw_text_with_background(display_frame, "ESPACE: Capturer | R: Auto | Q: Quitter", (10, 30))

            # Mode auto reconnaissance (toutes les 30 frames)
            if auto_recognize and frame_count % 30 == 0:
                print("🔍 Reconnaissance automatique...")
                result = recognize_face(frame)

                if result:
                    user = find_user_from_image_path(users_db, result['matched_image'])
                    if user:
                        last_recognition = {
                            'user': user,
                            'confidence': result['confidence'],
                            'timestamp': datetime.now()
                        }
                        print(f"   ✅ Reconnu: {user['full_name']} ({result['confidence']:.1f}%)")
                else:
                    last_recognition = None

            # Afficher le dernier résultat de reconnaissance
            if last_recognition:
                user = last_recognition['user']
                confidence = last_recognition['confidence']

                # Rectangle vert pour "reconnu"
                cv2.rectangle(display_frame, (10, 60), (400, 180), COLOR_GREEN, 2)

                # Informations
                draw_text_with_background(display_frame, "✓ RECONNU", (20, 90), 0.8, 2)
                draw_text_with_background(display_frame, f"Nom: {user['full_name']}", (20, 120), 0.6, 1)
                draw_text_with_background(display_frame, f"Email: {user['email']}", (20, 145), 0.6, 1)
                draw_text_with_background(display_frame, f"Confiance: {confidence:.1f}%", (20, 170), 0.6, 1)

            # Indicateur mode auto
            if auto_recognize:
                draw_text_with_background(display_frame, "MODE AUTO ACTIF", (10, display_frame.shape[0] - 20), 0.6, 2)

            # Afficher la frame
            cv2.imshow('Reconnaissance Faciale - Webcam', display_frame)

            frame_count += 1

            # Gestion des touches
            key = cv2.waitKey(1) & 0xFF

            # ESPACE: Capture manuelle
            if key == ord(' '):
                print("\n📸 Capture en cours...")
                result = recognize_face(frame)

                if result:
                    user = find_user_from_image_path(users_db, result['matched_image'])

                    if user:
                        print("=" * 60)
                        print("✅ VISAGE RECONNU!")
                        print(f"   👤 Nom: {user['full_name']}")
                        print(f"   🔑 Username: {user['username']}")
                        print(f"   📧 Email: {user['email']}")
                        print(f"   📊 Confiance: {result['confidence']:.2f}%")
                        print(f"   📏 Distance: {result['distance']:.4f}")
                        print("=" * 60)
                        print()

                        last_recognition = {
                            'user': user,
                            'confidence': result['confidence'],
                            'timestamp': datetime.now()
                        }
                    else:
                        print("⚠️  Image trouvée mais utilisateur non identifié")
                        last_recognition = None
                else:
                    print("❌ Aucun visage reconnu")
                    last_recognition = None

            # R: Toggle mode auto
            elif key == ord('r') or key == ord('R'):
                auto_recognize = not auto_recognize
                status = "ACTIVÉ" if auto_recognize else "DÉSACTIVÉ"
                print(f"\n🔄 Mode reconnaissance automatique: {status}\n")

            # Q: Quitter
            elif key == ord('q') or key == ord('Q'):
                print("\n👋 Arrêt du programme...")
                break

    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption par l'utilisateur")

    finally:
        # Libérer les ressources
        cap.release()
        cv2.destroyAllWindows()

        # Nettoyer les fichiers temporaires
        if os.path.exists(TEMP_TEST_IMAGE):
            os.remove(TEMP_TEST_IMAGE)

        print("✅ Webcam fermée")
        print("🎬 Programme terminé\n")


if __name__ == "__main__":
    main()