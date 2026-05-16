from django.contrib import admin
from .models import Aliado, Repartidor, Cliente, Pedido, PedidoProducto, Producto, Ruta, RutaParada

admin.site.register(Aliado)
admin.site.register(Repartidor)
admin.site.register(Cliente)
admin.site.register(Producto)
admin.site.register(Pedido)
admin.site.register(PedidoProducto)
admin.site.register(Ruta)
admin.site.register(RutaParada)
