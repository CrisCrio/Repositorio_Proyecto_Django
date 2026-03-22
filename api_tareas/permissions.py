from rest_framework import permissions

class IsInstructor(permissions.BasePermission):
    """
    Permitir el acceso solo a usuarios con rol de instructor. Se asume que el rol del usuario se almacena en el atributo 'rol' del objeto user, que es establecido por la autenticación personalizada.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.rol == 'instructor')