import os

import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from backend.firebase_config import get_firestore_client
from firebase_admin import auth, firestore

# Inicializa Firebase sólo una vez

db = get_firestore_client()


class RegistroAPIView(APIView):
    """Endpoint público para registrar un nuevo aprendiz."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {"error": "Faltan credenciales"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = auth.create_user(email=email, password=password)

            # Permitir indicar el rol desde el request para pruebas.
            # Si no se especifica, por defecto se crea como aprendiz.
            rol = request.data.get('rol', 'aprendiz')

            db.collection('perfiles').document(user.uid).set(
                {
                    'email': email,
                    'rol': rol,
                    'fecha_registro': firestore.SERVER_TIMESTAMP,
                }
            )

            return Response(
                {"mensaje": "Usuario registrado correctamente", "uid": user.uid},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            error_str = str(e)

            # Si el usuario ya existe, actualizamos su contraseña para facilitar pruebas.
            if 'EMAIL_EXISTS' in error_str:
                try:
                    user = auth.get_user_by_email(email)
                    auth.update_user(user.uid, password=password)
                    return Response(
                        {
                            "mensaje": "Usuario ya existía; contraseña actualizada.",
                            "uid": user.uid,
                        },
                        status=status.HTTP_200_OK,
                    )
                except Exception as e2:
                    return Response(
                        {"error": f"No se pudo actualizar la contraseña: {str(e2)}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            return Response({"error": error_str}, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    """Endpoint público que valida las credenciales y obtiene el JWT de Firebase."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        api_key = os.getenv('FIREBASE_WEB_API_KEY')

        if not email or not password:
            return Response({"error": "Faltan credenciales"}, status=status.HTTP_400_BAD_REQUEST)

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }

        try:
            response = requests.post(url, json=payload)
            data = response.json()

            if response.status_code == 200:
                return Response(
                    {
                        "mensaje": "Login exitoso",
                        "token": data.get('idToken'),
                        "uid": data.get('localId'),
                    },
                    status=status.HTTP_200_OK,
                )

            error_msg = data.get('error', {}).get('message', 'Error desconocido')
            return Response(
                {"error": error_msg},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        except Exception:
            return Response(
                {"error": "Error de conexión"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
