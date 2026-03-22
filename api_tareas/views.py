from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import TareasSerializer
from .authentication import FirebaseAuthentication
from backend.firebase_config import get_firestore_client
from firebase_admin import firestore

db = get_firestore_client()

class TareaAPIView(APIView):
    #Traer el guardia de seguridad
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]

    """GET solo va a traer las tareas del usuario dueño del token."""

    def get(self, request, tarea_id=None):
        uid_usuario = request.user.uid
        rol_usuario = request.user.rol

        try:
            #trae todos los datos de la coleccion

            if rol_usuario == 'instructor':
                docs = db.collection('api_tareas').stream()
            else:
                docs = db.collection('api_tareas').where('uid_usuario', '==', uid_usuario).stream()

            tareas = []
            for doc in docs:
                tarea_data = doc.to_dict()
                tarea_data['id'] = doc.id
                tareas.append(tarea_data)

            return Response(
                {"mensaje": f"Listando tareas desde el rol de {rol_usuario}", "datos": tareas},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"mensaje":f"Error al obtener tareas: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def post(self, request):
        #1. pasar el JSON al serializador
        serializer = TareasSerializer(data=request.data)

        #2. si el JSON comple las reglas
        if serializer.is_valid():
            datos_validados = serializer.validated_data

            datos_validados['uid_usuario'] = request.user.uid
            datos_validados['fecha_creacion'] = firestore.SERVER_TIMESTAMP

            try:
                # ahora sí guardamos en firebase
                nuevo_doc = db.collection('api_tareas').add(datos_validados)
                id_generador = nuevo_doc[1].id

                return Response(
                    {"mensaje": "Tarea creada correctamente", "id": id_generador},
                    status=status.HTTP_201_CREATED,
                )
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, tarea_id):
        if not tarea_id:
            return Response({"error":"El ID es requerido"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            tarea_ref = db.collection('api_tareas').document(tarea_id)
            doc = tarea_ref.get()

            if not doc.exists:
                return Response({"error": "El ID no se ha encontrado"}, status=status.HTTP_404_NOT_FOUND)
                
            tarea_data = doc.to_dict()

            if tarea_data.get('uid_usuario') != request.user.uid:
                return Response({
                    "Error":"No tienes acceso a esta tarea"
                }, status= status.HTTP_403_FORBIDDEN)

            # 1.Pasamos los datos al serializados
            serializer = TareasSerializer(data=request.data, partial=True)

            if serializer.is_valid():
                #guarda los datos en firestore
                tarea_ref.update(serializer.validated_data)

                return Response({
                    "mensaje":f"Tarea {tarea_id} actualizada",
                    "datos": serializer.validated_data
                }, status= status.HTTP_200_OK)
            return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error":str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def delete(self,request, tarea_id=None):
        try:
            # Si el instructor solicita eliminar todo, le permitimos
            if tarea_id is None:
                if request.user.rol != 'instructor':
                    return Response({"error": "No tienes permiso para eliminar todas las tareas"}, status=status.HTTP_403_FORBIDDEN)

                docs = db.collection('api_tareas').stream()
                eliminadas = 0
                for doc in docs:
                    db.collection('api_tareas').document(doc.id).delete()
                    eliminadas += 1

                return Response({"mensaje": f"Se eliminaron {eliminadas} tareas"}, status=status.HTTP_200_OK)

            tarea_ref = db.collection('api_tareas').document(tarea_id)

            # Verificamos que exista
            if not tarea_ref.get().exists:
                return Response({"error": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)

            doc = tarea_ref.get()
            tarea_data = doc.to_dict()

            if tarea_data.get('uid_usuario') != request.user.uid:
                return Response(
                    {"error":"No tienes permiso para eliminar esta tarea"},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            tarea_ref.delete()
            return Response({"mensaje":f"Tarea {tarea_id} se ha eliminado correctamente"},
            status = status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )