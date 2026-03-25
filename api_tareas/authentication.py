from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from firebase_admin import auth
from backend.firebase_config import get_firestore_client
import firebase_admin

db = get_firestore_client()

class FirebaseAuthentication(BaseAuthentication):
    """
    Leer el tokenJWT del encabesado. Lova  a validar y v a extraer el UID del usuario
    """

    def authenticate(self, request):
        #extraeremos el token
        auth_header= request.META.get("HTTP_AUTHORIZATION") or request.headers.get('Authorization')
        if not auth_header:
            return None #No hay token
        
        #El token viene "Barer <<token>>"

        partes = auth_header.split()
        if len(partes) != 2 or partes[0].lower() != "bearer":
            raise AuthenticationFailed("Formato de autorización inválido")
        token = partes[1]

        try:
            #firebase va a validar la firma
            decoded_token = auth.verify_id_token(token)
            uid = decoded_token.get('uid')
            email = decoded_token.get('email')
            user_profile = db.collection('perfiles').document(uid).get()
            user_data = user_profile.to_dict() if user_profile.exists else {}
            rol = user_data.get('rol', 'aprendiz')  # Asignar 'aprendiz' por defecto si no se encuentra el rol
            class FirebaseUser:
                is_authenticated = True
                def __init__(self, uid, rol, email):
                    self.uid = uid
                    self.rol = rol
                    self.email = email
                    self.is_authenticated= True

            return (FirebaseUser(uid, rol, email), None)
        except Exception as e:
            raise AuthenticationFailed(f"Token no es válido: {str(e)}")