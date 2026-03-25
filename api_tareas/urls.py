from django.urls import path
from .views import TareaAPIView
from .views_auth import LoginAPIView, RegistroAPIView, PerfilAPIView, CambiarRolAPIView, ListarUsuariosAPIView
from .views_perfil import PerfilImagenAPIView

urlpatterns = [
    path('auth/registro/', RegistroAPIView.as_view(), name='api_registro'),
    path('auth/login/', LoginAPIView.as_view(), name='api_login'),

    path('tareas/', TareaAPIView.as_view(), name='api_tareas'),
    path('tareas/<str:tarea_id>/', TareaAPIView.as_view(), name='api_tarea_detalle'),

    path('perfil/', PerfilAPIView.as_view(), name='api_perfil'),         # ✅ línea nueva
    path('perfil/imagen/', PerfilImagenAPIView.as_view(), name='api_perfil_imagen'),

    path('usuarios/',              ListarUsuariosAPIView.as_view(), name='api_usuarios'),
    path('usuarios/<str:uid>/rol/', CambiarRolAPIView.as_view(),   name='api_cambiar_rol'),
]