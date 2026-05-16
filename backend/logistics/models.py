from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrador'),
        ('aliado', 'Aliado'),
        ('driver', 'Repartidor')
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='driver')
    nombre = models.CharField(max_length=100)
    estado = models.CharField(max_length=50, default='Disponible')
    ubicacion = models.CharField(max_length=200, default='Sin ubicación')

    def __str__(self):
        return f"{self.username} - {self.role}"

class Aliado(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'aliado'})
    direccion = models.CharField(max_length=200)
    latitud = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)

    def __str__(self):
        return self.user.nombre

class Repartidor(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'driver'})
    telefono = models.CharField(max_length=20, blank=True, null=True)
    latitud_actual = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud_actual = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    capacidad_maxima_kg = models.DecimalField(max_digits=8, decimal_places=2, default=15)
    volumen_maximo_m3 = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    # NUEVOS CAMPOS
    disponible = models.BooleanField(default=False, help_text="¿Disponible para recibir nuevas rutas?")
    ultima_ubicacion = models.JSONField(default=dict, blank=True, help_text="Última ubicación: {'lat': ..., 'lng': ...}")
    ultima_conexion = models.DateTimeField(null=True, blank=True, help_text="Última conexión registrada")

    def __str__(self):
        return self.user.nombre

class Producto(models.Model):
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, null=True)
    peso_kg = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    volumen_m3 = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)

    def __str__(self):
        return self.nombre

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    correo = models.EmailField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=200)
    latitud = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)

    def __str__(self):
        return self.nombre

class Pedido(models.Model):
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('normal', 'Normal'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    aliado = models.ForeignKey(Aliado, on_delete=models.SET_NULL, null=True, blank=True)
    repartidor = models.ForeignKey(CustomUser, related_name='pedidos_asignados', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'role': 'driver'})
    productos = models.ManyToManyField(Producto, through='PedidoProducto', blank=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=30, default='Pendiente', choices=[
        ('Pendiente', 'Pendiente'),
        ('Asignado', 'Asignado'),
        ('En ruta', 'En ruta'),
        ('Entregado', 'Entregado'),
        ('Cancelado', 'Cancelado')
    ])
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='normal')
    peso_total_kg = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    volumen_total_m3 = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    ventana_entrega_inicio = models.DateTimeField(null=True, blank=True)
    ventana_entrega_fin = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente.nombre}"

class PedidoProducto(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('pedido', 'producto')

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

class Ruta(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, null=True, blank=True)
    repartidor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'driver'})
    aliado = models.ForeignKey(Aliado, on_delete=models.SET_NULL, null=True, blank=True)
    latitud_inicio = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud_inicio = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    tiempo_estimado_mins = models.IntegerField(null=True, blank=True)
    distancia_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    estado_ruta = models.CharField(max_length=20, default='calculada', choices=[
        ('calculada', 'calculada'),
        ('asignada', 'asignada'),
        ('en_ruta', 'en_ruta'),
        ('completada', 'completada'),
        ('fallida', 'fallida')
    ])
    capacidad_usada_kg = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    geometria = models.JSONField(null=True, blank=True)
    decision_ai = models.JSONField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ruta {self.id} - {self.repartidor.nombre}"

class RutaParada(models.Model):
    ruta = models.ForeignKey(Ruta, related_name='paradas', on_delete=models.CASCADE)
    pedido = models.ForeignKey(Pedido, related_name='paradas_ruta', on_delete=models.CASCADE)
    orden = models.PositiveIntegerField()
    latitud = models.DecimalField(max_digits=10, decimal_places=8)
    longitud = models.DecimalField(max_digits=11, decimal_places=8)
    distancia_desde_anterior_km = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    tiempo_estimado_desde_anterior_mins = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=20, default='pendiente', choices=[
        ('pendiente', 'pendiente'),
        ('completada', 'completada'),
        ('fallida', 'fallida'),
    ])

    class Meta:
        ordering = ['orden']
        unique_together = ('ruta', 'pedido')

    def __str__(self):
        return f"Parada {self.orden} - Ruta {self.ruta_id}"
