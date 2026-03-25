import os

import requests
from rest_framework.permissions import IsAuthenticated
from .authentication import FirebaseAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from backend.firebase_config import get_firestore_client
from firebase_admin import auth, firestore

# Inicializa Firebase sólo una vez

db = get_firestore_client()

class PerfilAPIView(APIView):
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            doc = db.collection('perfiles').document(request.user.uid).get()
            data = doc.to_dict() if doc.exists else {}
            return Response({
                "email": request.user.email,
                "rol": data.get('rol', 'usuario'),
                "foto_perfil": data.get('photo_url', None),
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

class CambiarRolAPIView(APIView):
    """Solo el rol 'coordinador' puede cambiar roles de otros usuarios."""
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, uid):
        # Solo coordinador puede cambiar roles
        if request.user.rol != 'coordinador':
            return Response(
                {"error": "No tienes permiso para cambiar roles"},
                status=status.HTTP_403_FORBIDDEN
            )

        nuevo_rol = request.data.get('rol')
        roles_validos = ['aprendiz', 'instructor', 'coordinador']

        if not nuevo_rol or nuevo_rol not in roles_validos:
            return Response(
                {"error": f"Rol inválido. Debe ser uno de: {roles_validos}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Actualiza el rol en Firestore
            db.collection('perfiles').document(uid).update({'rol': nuevo_rol})
            return Response(
                {"mensaje": f"Rol actualizado correctamente a '{nuevo_rol}'"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ListarUsuariosAPIView(APIView):
    """Lista todos los usuarios. Solo coordinador e instructor pueden acceder."""
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.rol not in ['coordinador', 'instructor']:
            return Response(
                {"error": "No tienes permiso para ver esta información"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Filtra por rol si se pasa como query param
            # Ejemplo: /api/usuarios/?rol=aprendiz
            rol_filtro = request.query_params.get('rol', None)

            if rol_filtro:
                docs = db.collection('perfiles').where('rol', '==', rol_filtro).stream()
            else:
                docs = db.collection('perfiles').stream()

            usuarios = []
            for doc in docs:
                data = doc.to_dict()
                usuarios.append({
                    "uid": doc.id,
                    "email": data.get('email', ''),
                    "rol": data.get('rol', 'aprendiz'),
                    "foto_perfil": data.get('photo_url', None),
                    "fecha_registro": str(data.get('fecha_registro', '')),
                })

            return Response(
                {"datos": usuarios, "total": len(usuarios)},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )