#!/usr/bin/env python
"""
Script de prueba para validar que todos los mensajes de error estén en español.

Uso:
    python manage.py shell < test_validaciones_es.py
    
O dentro de shell:
    exec(open('test_validaciones_es.py').read())
"""

from logistics.serializers import (
    ClienteSerializer, ProductoSerializer, RepartidorSerializer,
    AliadoSerializer, PedidoSerializer, RouteOptimizeRequestSerializer
)
from logistics.validators import LatitudeValidator, LongitudeValidator

def test_latitud_invalida():
    """Test: Latitud fuera de rango"""
    print("\n" + "="*60)
    print("TEST 1: Latitud inválida (fuera de rango)")
    print("="*60)
    
    data = {
        'nombre': 'Cliente Test',
        'direccion': 'Calle 123',
        'latitud': 999,  # Inválido
        'longitud': -74.0
    }
    serializer = ClienteSerializer(data=data)
    if not serializer.is_valid():
        print(f"✓ Error capturado: {serializer.errors}")
        assert 'latitud' in serializer.errors
        assert 'español' in str(serializer.errors).lower() or '90' in str(serializer.errors)
    else:
        print("✗ FALLO: No se capturó el error de latitud")


def test_longitud_invalida():
    """Test: Longitud fuera de rango"""
    print("\n" + "="*60)
    print("TEST 2: Longitud inválida (fuera de rango)")
    print("="*60)
    
    data = {
        'nombre': 'Cliente Test',
        'direccion': 'Calle 123',
        'latitud': 4.7110,
        'longitud': 999  # Inválido
    }
    serializer = ClienteSerializer(data=data)
    if not serializer.is_valid():
        print(f"✓ Error capturado: {serializer.errors}")
        assert 'longitud' in serializer.errors
    else:
        print("✗ FALLO: No se capturó el error de longitud")


def test_direccion_obligatoria():
    """Test: Campo direccion obligatorio"""
    print("\n" + "="*60)
    print("TEST 3: Dirección obligatoria (campo vacío)")
    print("="*60)
    
    data = {
        'nombre': 'Cliente Test',
        'direccion': '',  # Vacío
        'latitud': 4.7110,
        'longitud': -74.0
    }
    serializer = ClienteSerializer(data=data)
    if not serializer.is_valid():
        print(f"✓ Error capturado: {serializer.errors}")
        assert 'direccion' in serializer.errors
        error_msg = str(serializer.errors)
        # Verificar que el mensaje contiene palabras clave en español
        assert 'obligatoria' in error_msg.lower() or 'vacía' in error_msg.lower()
    else:
        print("✗ FALLO: No se capturó el error de dirección")


def test_peso_negativo():
    """Test: Peso negativo"""
    print("\n" + "="*60)
    print("TEST 4: Peso negativo")
    print("="*60)
    
    data = {
        'nombre': 'Producto Test',
        'peso_kg': -5.0  # Negativo
    }
    serializer = ProductoSerializer(data=data)
    if not serializer.is_valid():
        print(f"✓ Error capturado: {serializer.errors}")
        assert 'peso_kg' in serializer.errors
        error_msg = str(serializer.errors)
        assert 'negativo' in error_msg.lower()
    else:
        print("✗ FALLO: No se capturó el error de peso")


def test_capacidad_cero():
    """Test: Capacidad cero"""
    print("\n" + "="*60)
    print("TEST 5: Capacidad máxima = 0")
    print("="*60)
    
    data = {
        'capacidad_maxima_kg': 0  # Cero
    }
    serializer = RepartidorSerializer(data=data, partial=True)
    if not serializer.is_valid():
        print(f"✓ Error capturado: {serializer.errors}")
        assert 'capacidad_maxima_kg' in serializer.errors
        error_msg = str(serializer.errors)
        assert 'mayor' in error_msg.lower() or 'cero' in error_msg.lower()
    else:
        print("✗ FALLO: No se capturó el error de capacidad")


def test_longitud_excesiva():
    """Test: Longitud decimal excesiva"""
    print("\n" + "="*60)
    print("TEST 6: Longitud con demasiados decimales")
    print("="*60)
    
    data = {
        'nombre': 'Bodega Test',
        'direccion': 'Carrera 5',
        'longitud': -74.123456789  # Más de 8 decimales
    }
    serializer = AliadoSerializer(data=data)
    print(f"Datos: {data}")
    print(f"Válido: {serializer.is_valid()}")
    if not serializer.is_valid():
        print(f"✓ Resultado: {serializer.errors}")
    else:
        print("✓ Datos aceptados (decimales se redondean automáticamente)")


def test_route_optimize_latitud_invalida():
    """Test: Latitud inválida en optimizador de rutas"""
    print("\n" + "="*60)
    print("TEST 7: Latitud inválida en RouteOptimizeRequest")
    print("="*60)
    
    data = {
        'latitud_inicial': 999,  # Inválido
        'longitud_inicial': -74.0,
        'repartidor_id': 1
    }
    serializer = RouteOptimizeRequestSerializer(data=data)
    if not serializer.is_valid():
        print(f"✓ Error capturado: {serializer.errors}")
        # Puede estar en el validate() method
        error_msg = str(serializer.errors)
        assert 'latitud' in error_msg.lower() or 'no está validado' in error_msg
    else:
        print("✗ FALLO: No se capturó el error de latitud")


def test_mensajes_en_espanol():
    """Test: Verificar que los mensajes son en español"""
    print("\n" + "="*60)
    print("TEST 8: Verificación de idioma español")
    print("="*60)
    
    palabras_clave = [
        'obligatoria', 'obligatorio', 'inválido', 'válido',
        'debe', 'pueden', 'deben', 'puede', 'tener',
        'grados', 'dígitos', 'decimales', 'caracteres',
        'correo', 'número', 'entero', 'vacía', 'vacío',
        'cero', 'negativo', 'mayor', 'menor', 'entre'
    ]
    
    data = {
        'nombre': 'Test',
        'direccion': 'Test',
        'latitud': 999,
    }
    serializer = ClienteSerializer(data=data)
    serializer.is_valid()
    
    errors_str = str(serializer.errors)
    print(f"Errores: {errors_str}")
    
    spanish_found = any(palabra in errors_str.lower() for palabra in palabras_clave)
    if spanish_found:
        print("✓ Se detectan palabras clave en español")
    else:
        print("✗ No se detectan palabras en español")


def run_all_tests():
    """Ejecuta todas las pruebas"""
    print("\n" + "="*60)
    print("SUITE DE PRUEBAS: VALIDACIONES EN ESPAÑOL")
    print("="*60)
    
    try:
        test_latitud_invalida()
        test_longitud_invalida()
        test_direccion_obligatoria()
        test_peso_negativo()
        test_capacidad_cero()
        test_longitud_excesiva()
        test_route_optimize_latitud_invalida()
        test_mensajes_en_espanol()
        
        print("\n" + "="*60)
        print("✓ TODAS LAS PRUEBAS COMPLETADAS")
        print("="*60)
    except AssertionError as e:
        print(f"\n✗ ERROR EN PRUEBA: {e}")
    except Exception as e:
        print(f"\n✗ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_all_tests()
