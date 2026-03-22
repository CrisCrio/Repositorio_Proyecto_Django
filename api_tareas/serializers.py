from rest_framework import serializers

class TareasSerializer(serializers.Serializer):
    """
    Validar los datos entrantes (JSON) ANTES DE ENVIARLOS A firestores
    """
    titulo = serializers.CharField(max_length=100)
    descripcion = serializers.CharField()
    estado = serializers.CharField(default = "Pendiente", max_length=20, required = False)

    def validate_titulo(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("El titulo debe tener al menos 5 caracteres")
        return value
