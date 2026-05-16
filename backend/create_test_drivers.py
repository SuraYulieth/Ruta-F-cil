#!/usr/bin/env python
"""
Script para poblar repartidores de prueba en la BD.
Crea repartidores con coordenadas en Bogotá.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from logistics.models import CustomUser, Repartidor

def populate_drivers():
    print("\n" + "="*80)
    print("CREANDO REPARTIDORES DE PRUEBA")
    print("="*80 + "\n")
    
    drivers_data = [
        {
            'username': 'carlos_driver',
            'nombre': 'Carlos Mendoza',
            'telefono': '3001111111',
            'latitud_actual': 4.7100,
            'longitud_actual': -74.0700,
            'capacidad_maxima_kg': 12,
        },
        {
            'username': 'ana_driver',
            'nombre': 'Ana Gómez',
            'telefono': '3002222222',
            'latitud_actual': 4.7160,
            'longitud_actual': -74.0780,
            'capacidad_maxima_kg': 15,
        },
        {
            'username': 'luis_driver',
            'nombre': 'Luis Ramírez',
            'telefono': '3003333333',
            'latitud_actual': 4.7040,
            'longitud_actual': -74.0670,
            'capacidad_maxima_kg': 10,
        },
    ]
    
    created = 0
    for data in drivers_data:
        username = data.pop('username')
        nombre = data.pop('nombre')
        
        user, user_created = CustomUser.objects.get_or_create(
            username=username,
            defaults={
                'nombre': nombre,
                'role': 'driver',
                'estado': 'Disponible',
            }
        )
        
        if user_created:
            user.set_password('123')
            user.save()
            print(f"✓ Usuario creado: {username}")
        else:
            print(f"→ Usuario ya existe: {username}")
        
        repartidor, rep_created = Repartidor.objects.get_or_create(
            user=user,
            defaults=data,
        )
        
        if rep_created:
            created += 1
            print(f"  ✓ Repartidor creado: {nombre}")
            print(f"    Coordenadas: ({data['latitud_actual']}, {data['longitud_actual']})")
            print(f"    Capacidad: {data['capacidad_maxima_kg']} kg\n")
        else:
            print(f"  → Repartidor ya existe para {nombre}\n")
    
    print("="*80)
    print(f"Resumen: {created} repartidor(es) nuevo(s) creado(s)")
    print("="*80 + "\n")
    
    # Mostrar repartidores creados
    from logistics.models import Repartidor as Rep
    total = Rep.objects.count()
    print(f"Total de repartidores en BD: {total}\n")
    
    for rep in Rep.objects.select_related('user').all():
        print(f"  - {rep.user.nombre} (ID: {rep.user.id})")
        print(f"    Disponible: {rep.user.estado == 'Disponible'}")
        print(f"    Coordenadas: ({rep.latitud_actual}, {rep.longitud_actual})")

if __name__ == '__main__':
    populate_drivers()
