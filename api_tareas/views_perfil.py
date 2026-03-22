import cloudinary
import cloudinary.uploader
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .authentication import FirebaseAuthentication
from backend.firebase_config import get_firestore_client

db = get_firestore_client()

class PerfilImagenAPIView(APIView):
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get("file") or request.data.get("file")
        if not file_obj:
            return Response({"error": "No file uploaded. Use field name 'file'."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = cloudinary.uploader.upload(
                file_obj,
                folder="perfil",
                public_id=f"profile_{request.user.uid}",
                overwrite=True,
                resource_type="auto",
            )
            url = result.get("secure_url") or result.get("url")
            if not url:
                raise ValueError("Cloudinary did not return a URL")

            # Guardar en Firestore el URL de la imagen de perfil
            db.collection("perfiles").document(request.user.uid).set(
                {"photo_url": url}, merge=True
            )

            return Response({"mensaje": "Imagen subida correctamente", "url": url}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
