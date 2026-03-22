# Importa Cloudinary principal para manejo de archivos multimedia en la nube
import cloudinary

# Importa uploader de Cloudinary para subir archivos
import cloudinary.uploader

# Importa APIView para crear vistas basadas en clases en Django REST Framework
from rest_framework.views import APIView

# Importa Response para devolver respuestas JSON al cliente
from rest_framework.response import Response

# Importa códigos HTTP como 200, 400, 500
from rest_framework import status

# Importa permiso para exigir autenticación del usuario
from rest_framework.permissions import IsAuthenticated

# Importa parsers para recibir archivos tipo multipart/form-data
from rest_framework.parsers import MultiPartParser, FormParser

# Importa autenticación personalizada con Firebase
from .authentication import FirebaseAuthentication

# Importa conexión con Firestore
from backend.firebase_config import get_firestore_client


# Crea conexión global con Firestore
db = get_firestore_client()


# Clase API para manejar imagen de perfil del usuario
class PerfilImagenAPIView(APIView):

    # Usa autenticación personalizada de Firebase
    authentication_classes = [FirebaseAuthentication]

    # Solo usuarios autenticados pueden acceder
    permission_classes = [IsAuthenticated]

    # Permite recibir archivos enviados desde formularios o Postman
    parser_classes = [MultiPartParser, FormParser]


    # =========================
    # MÉTODO POST (Subir imagen)
    # =========================
    def post(self, request):

        # Busca archivo enviado con nombre "file"
        # Puede venir en request.FILES o request.data
        file_obj = request.FILES.get("file") or request.data.get("file")

        # Si no se envía archivo devuelve error
        if not file_obj:
            return Response(
                {"error": "No file uploaded. Use field name 'file'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Sube archivo a Cloudinary
            result = cloudinary.uploader.upload(

                # Archivo recibido
                file_obj,

                # Carpeta donde se guardará en Cloudinary
                folder="perfil",

                # Nombre único basado en UID del usuario
                public_id=f"profile_{request.user.uid}",

                # Sobrescribe imagen anterior si ya existe
                overwrite=True,

                # Detecta automáticamente tipo de archivo
                resource_type="auto",
            )

            # Obtiene URL segura HTTPS
            url = result.get("secure_url") or result.get("url")

            # Si Cloudinary no devuelve URL genera error
            if not url:
                raise ValueError("Cloudinary did not return a URL")

            # Guarda URL de imagen en Firestore
            db.collection("perfiles").document(request.user.uid).set(

                # Campo photo_url
                {"photo_url": url},

                # Merge=True evita borrar otros campos existentes
                merge=True
            )

            # Devuelve respuesta exitosa con URL
            return Response(
                {
                    "mensaje": "Imagen subida correctamente",
                    "url": url
                },
                status=status.HTTP_200_OK
            )

        # Manejo de errores internos
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )