#!/usr/bin/env python
"""
Script de auditoría: Diagnostica por qué el optimizador no detecta repartidores.
Muestra todos los repartidores, sus estados y coordenadas disponibles.
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from logistics.models import Repartidor, CustomUser
from logistics.services.route_optimizer_service import RouteOptimizerService

def audit_drivers():
    print("\n" + "="*80)
    print("AUDITORÍA DE REPARTIDORES")
    print("="*80)

    all_drivers = Repartidor.objects.select_related('user').all()
    print(f"\nTotal de repartidores en BD: {all_drivers.count()}")

    if not all_drivers.exists():
        print("⚠️  No hay repartidores en la base de datos.")
        return

    print("\n" + "-"*80)
    print("DETALLES POR REPARTIDOR:")
    print("-"*80)

    for driver in all_drivers:
        print(f"\n📦 Repartidor ID: {driver.user_id}")
        print(f"   Nombre: {driver.user.nombre}")
        print(f"   Username: {driver.user.username}")
        print(f"   Role: {driver.user.role}")
        
        # Estado
        print(f"   Estado usuario: '{driver.user.estado}' (case-sensitive)")
        estado_lower = driver.user.estado.lower() if driver.user.estado else ""
        matches_disponible = estado_lower == 'disponible'
        print(f"      ➜ ¿Es 'Disponible' (case-insensitive)? {matches_disponible}")
        
        # Coordenadas
        print(f"\n   Coordenadas:")
        print(f"      latitud_actual: {driver.latitud_actual}")
        print(f"      longitud_actual: {driver.longitud_actual}")
        
        # Verificar con el helper del optimizador
        service = RouteOptimizerService()
        coords = service._get_driver_coordinates(driver)
        
        print(f"\n   Resultado del helper _get_driver_coordinates:")
        if coords:
            print(f"      ✓ Coordenadas detectadas: lat={coords[0]}, lng={coords[1]}")
        else:
            print(f"      ✗ No se detectaron coordenadas válidas")
        
        # Verificar disponibilidad para el optimizador
        will_be_selected = matches_disponible and coords is not None
        print(f"\n   ¿Será detectado por el optimizador?")
        if will_be_selected:
            print(f"      ✓ SÍ - Estado disponible y tiene coordenadas")
        else:
            if not matches_disponible:
                print(f"      ✗ NO - Estado '{driver.user.estado}' no es 'Disponible'")
            if not coords:
                print(f"      ✗ NO - Sin coordenadas válidas")

    # Resumen
    print("\n" + "-"*80)
    print("RESUMEN:")
    print("-"*80)
    
    available = 0
    for driver in all_drivers:
        service = RouteOptimizerService()
        coords = service._get_driver_coordinates(driver)
        estado_match = driver.user.estado.lower() == 'disponible'
        if estado_match and coords:
            available += 1
    
    print(f"Total repartidores con estado 'Disponible' y coordenadas: {available}")
    print(f"Total repartidores sin coordenadas: {all_drivers.filter(latitud_actual__isnull=True).count()}")
    
    estados = {}
    for driver in all_drivers:
        estado = driver.user.estado
        estados[estado] = estados.get(estado, 0) + 1
    
    print(f"\nEstados encontrados:")
    for estado, count in estados.items():
        print(f"  - '{estado}': {count}")

    # Verificar que campos tiene repartidores
    print(f"\nAnálisis de campos de coordenadas:")
    with_latitud_actual = all_drivers.filter(latitud_actual__isnull=False).count()
    with_longitud_actual = all_drivers.filter(longitud_actual__isnull=False).count()
    
    print(f"  - latitud_actual: {with_latitud_actual}/{all_drivers.count()}")
    print(f"  - longitud_actual: {with_longitud_actual}/{all_drivers.count()}")

    print("\n" + "="*80)
    print("FIN DE AUDITORÍA")
    print("="*80 + "\n")

if __name__ == '__main__':
    audit_drivers()
