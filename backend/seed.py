import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from logistics.models import Aliado, Cliente, CustomUser, Pedido, Repartidor

def seed():
    # Limpiar datos previos si existieran
    Pedido.objects.all().delete()
    Repartidor.objects.all().delete()
    Aliado.objects.all().delete()
    Cliente.objects.all().delete()
    CustomUser.objects.all().delete()

    # 1. Crear Usuarios de acuerdo al mock del Frontend
    admin = CustomUser.objects.create_superuser(
        username='admin',
        role='admin',
        nombre='Super Admin'
    )
    admin.set_password('123')
    admin.save()

    carlos = CustomUser.objects.create(
        username='carlos', role='driver', nombre='Carlos Mendoza', estado='Disponible', ubicacion='Zona Norte'
    )
    carlos.set_password('123')
    carlos.save()

    ana = CustomUser.objects.create(
        username='ana', role='driver', nombre='Ana Gómez', estado='Disponible', ubicacion='Centro'
    )
    ana.set_password('123')
    ana.save()

    luis = CustomUser.objects.create(
        username='luis', role='driver', nombre='Luis Ramírez', estado='Ocupado', ubicacion='Zona Sur'
    )
    luis.set_password('123')
    luis.save()

    maria = CustomUser.objects.create(
        username='maria', role='driver', nombre='María Torres', estado='Disponible', ubicacion='Occidente'
    )
    maria.set_password('123')
    maria.save()

    Repartidor.objects.create(user=carlos, telefono='3001111111', latitud_actual=4.7100, longitud_actual=-74.0700, capacidad_maxima_kg=12)
    Repartidor.objects.create(user=ana, telefono='3002222222', latitud_actual=4.7160, longitud_actual=-74.0780, capacidad_maxima_kg=15)
    Repartidor.objects.create(user=luis, telefono='3003333333', latitud_actual=4.7040, longitud_actual=-74.0670, capacidad_maxima_kg=10)
    Repartidor.objects.create(user=maria, telefono='3004444444', latitud_actual=4.7210, longitud_actual=-74.0710, capacidad_maxima_kg=18)

    bodega_norte_user = CustomUser.objects.create(
        username='bodega_norte', role='aliado', nombre='Bodega Norte', estado='Disponible', ubicacion='Zona Norte'
    )
    bodega_norte_user.set_password('123')
    bodega_norte_user.save()
    bodega_centro_user = CustomUser.objects.create(
        username='bodega_centro', role='aliado', nombre='Bodega Centro', estado='Disponible', ubicacion='Centro'
    )
    bodega_centro_user.set_password('123')
    bodega_centro_user.save()

    bodega_norte = Aliado.objects.create(user=bodega_norte_user, direccion='Calle 80 # 20-10', latitud=4.7190, longitud=-74.0735)
    bodega_centro = Aliado.objects.create(user=bodega_centro_user, direccion='Carrera 10 # 20-30', latitud=4.7080, longitud=-74.0705)

    # 2. Crear Clientes
    c1 = Cliente.objects.create(nombre='Restaurante El Buen Sabor', direccion='Calle 45 # 12-34', latitud=4.7110, longitud=-74.0721)
    c2 = Cliente.objects.create(nombre='Farmacia San Juan', direccion='Avenida Siempre Viva 742', latitud=4.7152, longitud=-74.0764)
    c3 = Cliente.objects.create(nombre='Supermercado Central', direccion='Carrera 15 # 8-20', latitud=4.7038, longitud=-74.0677)
    c4 = Cliente.objects.create(nombre='Tienda La Esquina', direccion='Calle 100 # 50-10', latitud=4.7205, longitud=-74.0699)

    # 3. Crear Pedidos
    Pedido.objects.create(cliente=c1, estado='Pendiente', prioridad='alta', peso_total_kg=2.5, aliado=bodega_centro)
    Pedido.objects.create(cliente=c2, estado='Pendiente', prioridad='normal', peso_total_kg=1.2, aliado=bodega_norte)
    Pedido.objects.create(cliente=c3, estado='En ruta', repartidor=luis)
    Pedido.objects.create(cliente=c4, estado='Pendiente', prioridad='urgente', peso_total_kg=3.0)

    print("Datos sembrados correctamente de acuerdo al mock del Frontend.")

if __name__ == '__main__':
    seed()
