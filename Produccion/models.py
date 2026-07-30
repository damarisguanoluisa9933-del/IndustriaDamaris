from django.db import models
from django.contrib.auth.models import User

# 1. LÍNEAS DE ENSAMBLAJE
class LineaEnsamblaje(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    foto = models.ImageField(upload_to='lineas/', blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


# 2. MAQUINARIA DE PLANTA
class Maquinaria(models.Model):
    ESTADOS = (
        ('Operativa', 'Operativa'),
        ('En Mantenimiento', 'En Mantenimiento'),
        ('Detenida', 'Detenida'),
        ('Falla', 'Falla'),
        ('Inactiva', 'Inactiva'),
    )
    nombre = models.CharField(max_length=100)
    codigo_inventario = models.CharField(max_length=50, unique=True)
    linea = models.ForeignKey(LineaEnsamblaje, on_delete=models.CASCADE, related_name='maquinarias')
    estado = models.CharField(max_length=30, choices=ESTADOS, default='Operativa')
    horas_uso = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    foto = models.ImageField(upload_to='maquinarias/', blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} [{self.estado}]"


# 3. SUPERVISORES (PERFIL DE USUARIO)
class Supervisor(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_supervisor', null=True, blank=True)
    cedula = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    correo = models.EmailField(unique=True)
    foto = models.ImageField(upload_to='supervisores/', blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


# 4. OPERARIOS DE PLANTA
class Operario(models.Model):
    cedula = models.CharField(max_length=10, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15)
    correo = models.EmailField(blank=True, null=True)
    foto = models.ImageField(upload_to='operarios/', blank=True, null=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


# 5. MATERIA PRIMA E INSUMOS
class Insumo(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=50, unique=True)
    unidad_medida = models.CharField(max_length=20) # Ej: kg, metros, litros, unidades
    stock_disponible = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    foto = models.ImageField(upload_to='insumos/', blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} ({self.unidad_medida})"


# 6. ÓRDENES DE FABRICACIÓN (LOTES)
class OrdenFabricacion(models.Model):
    ESTADOS_ORDEN = (
        ('Pendiente', 'Pendiente'),
        ('En Proceso', 'En Proceso'),
        ('Finalizada', 'Finalizada'),
    )
    codigo_lote = models.CharField(max_length=50, unique=True)
    producto = models.CharField(max_length=150)
    linea = models.ForeignKey(LineaEnsamblaje, on_delete=models.CASCADE)
    maquina = models.ForeignKey(Maquinaria, on_delete=models.SET_NULL, null=True, blank=True)
    supervisor = models.ForeignKey(Supervisor, on_delete=models.CASCADE)
    operario_encargado = models.ForeignKey(Operario, on_delete=models.SET_NULL, null=True, blank=True)
    
    cantidad_programada = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cantidad_producida = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    fecha_inicio_programada = models.DateTimeField()
    fecha_fin_programada = models.DateTimeField()
    prioridad_orden = models.IntegerField(default=1)
    estado = models.CharField(max_length=20, choices=ESTADOS_ORDEN, default='Pendiente')

    def __str__(self):
        return f"Lote {self.codigo_lote} - {self.producto}"


# 7. DETALLE DE MATERIA PRIMA Y CÁLCULO AUTOMÁTICO DE MERMA (COMPLETAMENTE BLINDADO)
class DetalleInsumoLote(models.Model):
    orden = models.ForeignKey(OrdenFabricacion, on_delete=models.CASCADE, related_name='detalles_insumos')
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE)
    cantidad_estimada = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cantidad_utilizada = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cantidad_desperdicio = models.DecimalField(max_digits=10, decimal_places=2, default=0)


# 8. REGISTRO AUTOMÁTICO DE INTERRUPCIONES
class RegistroInterrupcion(models.Model):
    maquina = models.ForeignKey(Maquinaria, on_delete=models.CASCADE)
    motivo = models.CharField(max_length=255)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Interrupción {self.maquina.nombre} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"