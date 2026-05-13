from django.contrib import admin
from .models import Aliado, Repartidor, Cliente, Pedido, Ruta

admin.site.register(Aliado)
admin.site.register(Repartidor)
admin.site.register(Cliente)
admin.site.register(Pedido)
admin.site.register(Ruta)
