from django.db import models
from django.contrib.auth.models import User

class Aliado(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    latitud = models.DecimalField(max_digits=10, decimal_places=8)
    longitud = models.DecimalField(max_digits=11, decimal_places=8)
    estado = models.CharField(max_length=20, default='activo', choices=[('activo', 'activo'), ('inactivo', 'inactivo')])

    def __str__(self):
        return self.nombre

class Repartidor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    latitud_actual = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitud_actual = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    estado = models.CharField(max_length=20, default='disponible', choices=[('disponible', 'disponible'), ('ocupado', 'ocupado'), ('desconectado', 'desconectado')])

    def __str__(self):
        return self.nombre

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    correo = models.EmailField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=200)
    latitud = models.DecimalField(max_digits=10, decimal_places=8)
    longitud = models.DecimalField(max_digits=11, decimal_places=8)

    def __str__(self):
        return self.nombre

class Pedido(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    aliado = models.ForeignKey(Aliado, on_delete=models.SET_NULL, null=True, blank=True)
    repartidor = models.ForeignKey(Repartidor, on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.TextField()
    estado = models.CharField(max_length=30, default='pendiente', choices=[
        ('pendiente', 'pendiente'),
        ('asignado', 'asignado'),
        ('en_transito', 'en_transito'),
        ('entregado', 'entregado'),
        ('cancelado', 'cancelado')
    ])
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente.nombre}"

class Ruta(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    repartidor = models.ForeignKey(Repartidor, on_delete=models.CASCADE)
    tiempo_estimado_mins = models.IntegerField(null=True, blank=True)
    distancia_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    estado_ruta = models.CharField(max_length=20, default='calculada', choices=[
        ('calculada', 'calculada'),
        ('completada', 'completada'),
        ('fallida', 'fallida')
    ])
    fecha_creacion = models.DateTimeField(auto_now_add=True)
