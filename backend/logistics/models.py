from django.db import models
from django.contrib.auth.models import AbstractUser

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

    def __str__(self):
        return self.user.nombre

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
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    aliado = models.ForeignKey(Aliado, on_delete=models.SET_NULL, null=True, blank=True)
    repartidor = models.ForeignKey(CustomUser, related_name='pedidos_asignados', on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'role': 'driver'})
    descripcion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=30, default='Pendiente', choices=[
        ('Pendiente', 'Pendiente'),
        ('Asignado', 'Asignado'),
        ('En ruta', 'En ruta'),
        ('Entregado', 'Entregado'),
        ('Cancelado', 'Cancelado')
    ])
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente.nombre}"

class Ruta(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    repartidor = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': 'driver'})
    tiempo_estimado_mins = models.IntegerField(null=True, blank=True)
    distancia_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    estado_ruta = models.CharField(max_length=20, default='calculada', choices=[
        ('calculada', 'calculada'),
        ('completada', 'completada'),
        ('fallida', 'fallida')
    ])
    fecha_creacion = models.DateTimeField(auto_now_add=True)
