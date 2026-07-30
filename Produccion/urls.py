from django.urls import path
from . import views

urlpatterns = [
    # AUTENTICACIÓN
    path('login/', views.vista_login, name='login'),
    path('registro/', views.vista_registro, name='registro'),
    path('logout/', views.vista_logout, name='cerrar_sesion'),

    # VISTAS PRINCIPALES
    path('', views.inicio, name='inicio'),
    path('inicio/', views.inicio, name='inicio'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # APIS AJAX PARA FUNCIONALIDADES INTERACTIVAS
    path('api/lotes_fullcalendar/', views.api_lotes_fullcalendar, name='api_lotes_fullcalendar'),
    path('api/reordenar_cola/', views.reordenar_cola_lotes, name='reordenar_cola_lotes'),
    path('api/cambiar_estado_hotkey/', views.cambiar_estado_maquina_hotkey, name='cambiar_estado_hotkey'),

    # LÍNEAS DE ENSAMBLAJE
    path('listado_lineas/', views.listado_lineas, name='listado_lineas'),
    path('nuevaLinea/', views.nueva_linea, name='nueva_linea'),
    path('editarLinea/<int:id>/', views.editar_linea, name='editar_linea'),
    path('eliminarLinea/<int:id>/', views.eliminar_linea, name='eliminar_linea'),

    # MAQUINARIA
    path('listado_maquinarias/', views.listado_maquinarias, name='listado_maquinarias'),
    path('nuevaMaquinaria/', views.nueva_maquinaria, name='nueva_maquinaria'),
    path('editarMaquinaria/<int:id>/', views.editar_maquinaria, name='editar_maquinaria'),
    path('eliminarMaquinaria/<int:id>/', views.eliminar_maquinaria, name='eliminar_maquinaria'),

    # SUPERVISORES
    path('listado_supervisores/', views.listado_supervisores, name='listado_supervisores'),
    path('nuevoSupervisor/', views.nuevo_supervisor, name='nuevo_supervisor'),
    path('editarSupervisor/<int:id>/', views.editar_supervisor, name='editar_supervisor'),
    path('eliminarSupervisor/<int:id>/', views.eliminar_supervisor, name='eliminar_supervisor'),

    # OPERARIOS
    path('listado_operarios/', views.listado_operarios, name='listado_operarios'),
    path('nuevoOperario/', views.nuevo_operario, name='nuevo_operario'),
    path('editarOperario/<int:id>/', views.editar_operario, name='editar_operario'),
    path('eliminarOperario/<int:id>/', views.eliminar_operario, name='eliminar_operario'),

    # INSUMOS
    path('listado_insumos/', views.listado_insumos, name='listado_insumos'),
    path('nuevoInsumo/', views.nuevo_insumo, name='nuevo_insumo'),
    path('editarInsumo/<int:id>/', views.editar_insumo, name='editar_insumo'),
    path('eliminarInsumo/<int:id>/', views.eliminar_insumo, name='eliminar_insumo'),

    # ÓRDENES DE FABRICACIÓN (LOTES)
    path('listado_ordenes/', views.listado_ordenes, name='listado_ordenes'),
    path('nuevaOrden/', views.nueva_orden, name='nueva_orden'),
    path('editarOrden/<int:id>/', views.editar_orden, name='editar_orden'),
    path('eliminarOrden/<int:id>/', views.eliminar_orden, name='eliminar_orden'),
    path('aprobar_orden/<int:id>/', views.aprobar_orden, name='aprobar_orden'),

    # REPORTES
    path('reporte_desperdicios/', views.reporte_desperdicios, name='reporte_desperdicios'),
]