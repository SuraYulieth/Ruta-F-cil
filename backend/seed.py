import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from logistics.models import Aliado, Repartidor, Cliente, Pedido

def seed():
    # Users
    u1, _ = User.objects.get_or_create(username='admin', is_staff=True, is_superuser=True)
    if _: u1.set_password('admin123'); u1.save()
    
    u2, _ = User.objects.get_or_create(username='carlos_m')
    u3, _ = User.objects.get_or_create(username='ana_g')
    u4, _ = User.objects.get_or_create(username='bodega_poblado')

    # Aliado
    aliado, _ = Aliado.objects.get_or_create(
        user=u4,
        nombre='Bodega El Poblado',
        direccion='Calle 10 # 43-21',
        latitud=6.2089,
        longitud=-75.5678
    )

    # Repartidores
    r1, _ = Repartidor.objects.get_or_create(
        user=u2,
        nombre='Carlos M.',
        latitud_actual=6.2100,
        longitud_actual=-75.5700,
        estado='ocupado'
    )
    r2, _ = Repartidor.objects.get_or_create(
        user=u3,
        nombre='Ana G.',
        latitud_actual=6.2050,
        longitud_actual=-75.5650,
        estado='disponible'
    )

    # Clientes
    c1, _ = Cliente.objects.get_or_create(
        nombre='David Restrepo',
        direccion='Circular 4 # 72-10',
        latitud=6.2442,
        longitud=-75.5891
    )
    c2, _ = Cliente.objects.get_or_create(
        nombre='Sura Rueda',
        direccion='Carrera 70 # 32-15',
        latitud=6.2308,
        longitud=-75.5905
    )

    # Pedidos
    Pedido.objects.get_or_create(cliente=c1, descripcion='Paquete pequeño - Electrónicos', estado='pendiente')
    Pedido.objects.get_or_create(cliente=c2, descripcion='Caja mediana - Ropa', estado='pendiente')

    print("Seed data created successfully!")

if __name__ == '__main__':
    seed()
