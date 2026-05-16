#!/usr/bin/env python
"""
Script para probar el endpoint /api/routes/optimize/ con modo multi_ruta
"""
import json
import urllib.request
import urllib.error

BASE_URL = 'http://127.0.0.1:8000'
ENDPOINT = '/api/routes/optimize/'

# Pedidos a optimizar
pedidos_candidatos = [15, 16, 17, 18]

payload = {
    'modo': 'multi_ruta',
    'pedidos_candidatos': pedidos_candidatos,
    'capacidad_maxima': 15,
}

print("\n" + "="*80)
print("PRUEBA DEL ENDPOINT /api/routes/optimize/")
print("="*80)
print(f"\nURL: {BASE_URL}{ENDPOINT}")
print(f"Método: POST")
print(f"Payload:")
print(json.dumps(payload, indent=2))
print("\n" + "-"*80)

try:
    req = urllib.request.Request(
        f"{BASE_URL}{ENDPOINT}",
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    with urllib.request.urlopen(req) as response:
        status_code = response.status
        response_data = json.loads(response.read().decode('utf-8'))
        
        print(f"\nEstatus: {status_code} ✓")
        print(f"\nRespuesta:")
        print(json.dumps(response_data, indent=2, ensure_ascii=False))
        
        # Análisis
        print("\n" + "-"*80)
        print("ANÁLISIS:")
        print("-"*80)
        
        if 'modo' in response_data:
            print(f"✓ Modo: {response_data['modo']}")
        
        if 'orden_entrega' in response_data:
            routes = response_data['orden_entrega']
            print(f"✓ Rutas creadas: {len(routes)}")
            for i, route in enumerate(routes, 1):
                print(f"\n  Ruta {i}:")
                print(f"    Repartidor ID: {route.get('repartidor_id')}")
                print(f"    Número de paradas: {len(route.get('paradas', []))}")
                print(f"    Pedidos asignados: {[p['id'] for p in route.get('paradas', [])]}")
                print(f"    Distancia: {route.get('distancia_km')} km")
                print(f"    Duración estimada: {route.get('tiempo_estimado_mins')} minutos")
        
        if 'pedidos_sin_asignar' in response_data:
            unassigned = response_data['pedidos_sin_asignar']
            if unassigned:
                print(f"\n⚠️  Pedidos sin asignar: {len(unassigned)}")
                for order in unassigned:
                    print(f"  - Pedido {order.get('pedido_id')}: {order.get('motivo')}")
        else:
            print(f"\n✓ Todos los pedidos fueron asignados")
            
except urllib.error.HTTPError as e:
    print(f"\n❌ Error HTTP {e.code}")
    try:
        error_response = json.loads(e.read().decode('utf-8'))
        print(f"Respuesta de error:")
        print(json.dumps(error_response, indent=2, ensure_ascii=False))
    except:
        print(e.read().decode('utf-8'))

except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "="*80 + "\n")
