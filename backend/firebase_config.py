import os
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, firestore

def get_firestore_client():

    file_name = os.getenv("FIREBASE_CREDENTIALS")

    if not file_name:
        raise ValueError("FIREBASE_CREDENTIALS no está definida en el .env")

    cert_path = os.path.join(settings.BASE_DIR, file_name)

    print("Ruta del certificado:", cert_path)

    if not firebase_admin._apps:
        cred = credentials.Certificate(cert_path)
        firebase_admin.initialize_app(cred)

    return firestore.client()