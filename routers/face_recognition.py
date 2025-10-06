"""
Router FastAPI pour la reconnaissance faciale
Fichier : routers/face_recognition.py
"""

from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from deepface import DeepFace
import os
import json
import shutil
from datetime import datetime, timedelta
import jwt

# Configuration - Chemins vers le dossier facial
FACE_DATABASE_DIR = "facial/face_database"
USERS_DB_FILE = "facial/users_database.json"
TEMP_DIR = "facial/temp_faces"

# Clé secrète JWT
SECRET_KEY = "votre-clé-secrète-super-sécurisée-changez-moi"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Créer le dossier temporaire
os.makedirs(TEMP_DIR, exist_ok=True)

# Créer le router
router = APIRouter(
    prefix="/api/face",
    tags=["Face Recognition"]
)

# Modèles Pydantic
class FaceLoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    user: Optional[dict] = None
    message: str
    confidence: Optional[float] = None

# ==================== UTILITAIRES ====================

def load_users_db():
    """Charger la base de données des utilisateurs"""
    if os.path.exists(USERS_DB_FILE):
        with open(USERS_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Créer un token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def find_user_from_image_path(users_db, image_path):
    """Trouver l'utilisateur correspondant à une image"""
    for user_id, user_data in users_db.items():
        if any(img in image_path for img in user_data['face_images']):
            return user_data
    return None

async def save_uploaded_file(file: UploadFile, destination: str) -> str:
    """Sauvegarder le fichier uploadé"""
    try:
        with open(destination, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return destination
    finally:
        file.file.close()

# ==================== ROUTES ====================

@router.post("/login", response_model=FaceLoginResponse)
async def face_login(face_image: UploadFile = File(...)):
    """
    🎭 Connexion par reconnaissance faciale

    - **face_image**: Image du visage (JPEG, PNG)
    - Retourne un token JWT si reconnu
    """

    # Vérifier le type de fichier
    if not face_image.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail="Le fichier doit être une image (JPEG, PNG, etc.)"
        )

    # Vérifier que la base de données existe
    if not os.path.exists(FACE_DATABASE_DIR):
        raise HTTPException(
            status_code=404,
            detail="Base de données faciale non trouvée. Exécutez build_face_database.py"
        )

    # Charger la base de données des utilisateurs
    users_db = load_users_db()

    if not users_db:
        raise HTTPException(
            status_code=404,
            detail="Aucun utilisateur enregistré"
        )

    # Sauvegarder temporairement l'image
    temp_image_path = os.path.join(TEMP_DIR, f"login_{datetime.utcnow().timestamp()}.jpg")

    try:
        await save_uploaded_file(face_image, temp_image_path)

        # Vérifier qu'un visage est détectable
        try:
            DeepFace.extract_faces(
                img_path=temp_image_path,
                detector_backend='opencv',
                enforce_detection=True
            )
        except Exception:
            os.remove(temp_image_path)
            raise HTTPException(
                status_code=400,
                detail="Aucun visage détecté dans l'image"
            )

        # Rechercher le visage
        result = DeepFace.find(
            img_path=temp_image_path,
            db_path=FACE_DATABASE_DIR,
            model_name='VGG-Face',
            detector_backend='opencv',
            distance_metric='cosine',
            enforce_detection=False,
            silent=True
        )

        # Vérifier si un match trouvé
        if len(result) > 0 and not result[0].empty:
            matched_image_path = result[0].iloc[0]['identity']
            distance = result[0].iloc[0]['distance']
            confidence = (1 - distance) * 100

            # Trouver l'utilisateur
            matched_user = find_user_from_image_path(users_db, matched_image_path)

            if matched_user:
                # Créer le token
                access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = create_access_token(
                    data={
                        "sub": matched_user["username"],
                        "user_id": matched_user["user_id"]
                    },
                    expires_delta=access_token_expires
                )

                os.remove(temp_image_path)

                return FaceLoginResponse(
                    success=True,
                    token=access_token,
                    user={
                        "id": matched_user["user_id"],
                        "username": matched_user["username"],
                        "email": matched_user["email"],
                        "full_name": matched_user["full_name"]
                    },
                    message=f"Connexion réussie ! Bienvenue {matched_user['full_name']}",
                    confidence=round(confidence, 2)
                )

        os.remove(temp_image_path)

        return FaceLoginResponse(
            success=False,
            message="Visage non reconnu"
        )

    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur: {str(e)}"
        )


@router.get("/users")
async def list_registered_users():
    """📋 Liste tous les utilisateurs"""
    users_db = load_users_db()

    if not users_db:
        return {"total_users": 0, "users": []}

    users_list = [
        {
            "user_id": user_data["user_id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "image_count": user_data["image_count"],
            "registered_at": user_data["registered_at"]
        }
        for user_data in users_db.values()
    ]

    return {"total_users": len(users_list), "users": users_list}


@router.get("/health")
async def health_check():
    """🏥 Vérifier l'état du système"""
    db_exists = os.path.exists(FACE_DATABASE_DIR)
    users_db = load_users_db()
    total_users = len(users_db)

    if not db_exists:
        return {
            "status": "ERROR",
            "database_exists": False,
            "total_users": 0,
            "message": "Base de données non trouvée"
        }

    return {
        "status": "OK",
        "database_exists": True,
        "total_users": total_users,
        "message": f"Système opérationnel avec {total_users} utilisateur(s)"
    }