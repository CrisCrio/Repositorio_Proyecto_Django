# Importa APIView para crear vistas basadas en clases en Django REST Framework
from rest_framework.views import APIView

# Importa Response para devolver respuestas JSON al cliente
from rest_framework.response import Response

# Importa status para usar códigos HTTP como 200, 404, 500, etc.
from rest_framework import status

# Importa permiso para exigir que el usuario esté autenticado
from rest_framework.permissions import IsAuthenticated

# Importa el serializador que valida y transforma los datos de tareas
from .serializers import TareasSerializer

# Importa la autenticación personalizada con Firebase
from .authentication import FirebaseAuthentication

# Importa la función que conecta con Firestore
from backend.firebase_config import get_firestore_client

# Importa utilidades de Firebase Firestore
from firebase_admin import firestore

# Crea conexión global con Firestore
db = get_firestore_client()


# Clase principal de la API para manejar tareas
class TareaAPIView(APIView):

    # Define autenticación personalizada usando Firebase
    authentication_classes = [FirebaseAuthentication]

    # Solo usuarios autenticados pueden acceder
    permission_classes = [IsAuthenticated]

    """
    GET solo traerá las tareas del usuario dueño del token.
    Si el usuario es instructor podrá ver todas las tareas.
    """

    # =========================
    # MÉTODO GET (Consultar tareas)
    # =========================
    def get(self, request, tarea_id=None):

        # Obtiene UID del usuario autenticado
        uid_usuario = request.user.uid

        # Obtiene rol del usuario autenticado
        rol_usuario = request.user.rol

        try:
            # Si el rol es instructor, obtiene todas las tareas
            if rol_usuario == 'instructor':
                docs = db.collection('api_tareas').stream()

            # Si no, solo obtiene las tareas del usuario autenticado
            else:
                docs = db.collection('api_tareas').where('uid_usuario', '==', uid_usuario).stream()

            # Lista donde se guardarán las tareas
            tareas = []

            # Recorre cada documento encontrado en Firestore
            for doc in docs:

                # Convierte el documento en diccionario
                tarea_data = doc.to_dict()

                # Agrega el ID del documento al diccionario
                tarea_data['id'] = doc.id

                # Añade la tarea a la lista
                tareas.append(tarea_data)

            # Devuelve respuesta exitosa con lista de tareas
            return Response(
                {
                    "mensaje": f"Listando tareas desde el rol de {rol_usuario}",
                    "datos": tareas
                },
                status=status.HTTP_200_OK,
            )

        # Si ocurre error devuelve error interno
        except Exception as e:
            return Response(
                {"mensaje": f"Error al obtener tareas: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    # =========================
    # MÉTODO POST (Crear tarea)
    # =========================
    def post(self, request):

        # Convierte el JSON recibido en un serializador
        serializer = TareasSerializer(data=request.data)

        # Verifica si los datos cumplen las reglas del serializador
        if serializer.is_valid():

            # Obtiene datos validados
            datos_validados = serializer.validated_data

            # Agrega UID del usuario autenticado
            datos_validados['uid_usuario'] = request.user.uid

            # Agrega fecha de creación automática desde servidor Firebase
            datos_validados['fecha_creacion'] = firestore.SERVER_TIMESTAMP

            try:
                # Guarda el nuevo documento en Firestore
                nuevo_doc = db.collection('api_tareas').add(datos_validados)

                # Obtiene ID generado automáticamente
                id_generador = nuevo_doc[1].id

                # Devuelve respuesta exitosa
                return Response(
                    {
                        "mensaje": "Tarea creada correctamente",
                        "id": id_generador
                    },
                    status=status.HTTP_201_CREATED,
                )

            # Manejo de errores internos
            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Si el serializador falla devuelve errores de validación
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    # =========================
    # MÉTODO PUT (Actualizar tarea)
    # =========================
    def put(self, request, tarea_id):

        # Verifica que llegue el ID
        if not tarea_id:
            return Response(
                {"error": "El ID es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Busca referencia del documento en Firestore
            tarea_ref = db.collection('api_tareas').document(tarea_id)

            # Obtiene documento
            doc = tarea_ref.get()

            # Si no existe devuelve 404
            if not doc.exists:
                return Response(
                    {"error": "El ID no se ha encontrado"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Convierte documento a diccionario
            tarea_data = doc.to_dict()

            # Verifica que la tarea pertenezca al usuario autenticado
            if tarea_data.get('uid_usuario') != request.user.uid:
                return Response(
                    {"Error": "No tienes acceso a esta tarea"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Carga datos nuevos en serializador
            serializer = TareasSerializer(data=request.data, partial=True)

            # Si los datos son válidos
            if serializer.is_valid():

                # Actualiza solo los campos enviados
                tarea_ref.update(serializer.validated_data)

                # Devuelve respuesta de éxito
                return Response(
                    {
                        "mensaje": f"Tarea {tarea_id} actualizada",
                        "datos": serializer.validated_data
                    },
                    status=status.HTTP_200_OK
                )

            # Si falla validación
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # Manejo de errores internos
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    # =========================
    # MÉTODO DELETE (Eliminar tarea)
    # =========================
    def delete(self, request, tarea_id=None):

        try:
            # Si no llega ID significa eliminar todo
            if tarea_id is None:

                # Solo instructor puede eliminar todas
                if request.user.rol != 'instructor':
                    return Response(
                        {"error": "No tienes permiso para eliminar todas las tareas"},
                        status=status.HTTP_403_FORBIDDEN
                    )

                # Obtiene todas las tareas
                docs = db.collection('api_tareas').stream()

                # Contador de eliminadas
                eliminadas = 0

                # Recorre y elimina cada documento
                for doc in docs:
                    db.collection('api_tareas').document(doc.id).delete()
                    eliminadas += 1

                # Devuelve cuántas fueron eliminadas
                return Response(
                    {"mensaje": f"Se eliminaron {eliminadas} tareas"},
                    status=status.HTTP_200_OK
                )

            # Si llega ID elimina una sola tarea
            tarea_ref = db.collection('api_tareas').document(tarea_id)

            # Verifica existencia
            if not tarea_ref.get().exists:
                return Response(
                    {"error": "No encontrado"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Obtiene documento
            doc = tarea_ref.get()
            tarea_data = doc.to_dict()

            # Verifica que pertenezca al usuario
            if tarea_data.get('uid_usuario') != request.user.uid:
                return Response(
                    {"error": "No tienes permiso para eliminar esta tarea"},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Elimina documento
            tarea_ref.delete()

            # Respuesta de éxito
            return Response(
                {"mensaje": f"Tarea {tarea_id} se ha eliminado correctamente"},
                status=status.HTTP_200_OK
            )

        # Manejo de errores internos
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )