import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from logistics.models import CustomUser, Cliente, Pedido

def seed():
    # Limpiar datos previos si existieran
    Pedido.objects.all().delete()
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

    # 2. Crear Clientes
    c1 = Cliente.objects.create(nombre='Restaurante El Buen Sabor', direccion='Calle 45 # 12-34')
    c2 = Cliente.objects.create(nombre='Farmacia San Juan', direccion='Avenida Siempre Viva 742')
    c3 = Cliente.objects.create(nombre='Supermercado Central', direccion='Carrera 15 # 8-20')
    c4 = Cliente.objects.create(nombre='Tienda La Esquina', direccion='Calle 100 # 50-10')

    # 3. Crear Pedidos
    Pedido.objects.create(cliente=c1, estado='Pendiente')
    Pedido.objects.create(cliente=c2, estado='Pendiente')
    Pedido.objects.create(cliente=c3, estado='En ruta', repartidor=luis)
    Pedido.objects.create(cliente=c4, estado='Pendiente')

    print("Datos sembrados correctamente de acuerdo al mock del Frontend.")

if __name__ == '__main__':
    seed()
