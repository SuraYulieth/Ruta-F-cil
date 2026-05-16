"""
SUITE DE PRUEBAS PARA OPTIMIZACIÓN CON RADIO MÁXIMO
Ruta Fácil - Mayo 2026

Pruebas unitarias e integración del nuevo sistema de optimización
con restricción de radio máximo de 382 km² (~11 km)
"""

from django.test import TestCase
from decimal import Decimal
import math

from logistics.models import Aliado, Cliente, CustomUser, Pedido, Repartidor
from logistics.services.route_optimizer_service import RouteOptimizerService, haversine_km
from logistics.services.geospatial_helpers import (
    GeoPoint,
    is_within_radius,
    cluster_by_radius,
    calculate_centroid,
    haversine_km as haversine_calc,
)
from logistics.services.ai_route_decision_service import AiRouteDecisionService
from logistics.config import MAX_ROUTE_RADIUS_KM, MAX_ROUTE_AREA_KM2


class GeoSpatialHelpersTests(TestCase):
    """Pruebas de funciones geoespaciales básicas."""

    def test_haversine_distance_zero(self):
        """Prueba: distancia entre el mismo punto debe ser 0."""
        distance = haversine_calc(4.7110, -74.0721, 4.7110, -74.0721)
        self.assertAlmostEqual(distance, 0, places=2)

    def test_haversine_distance_known_points(self):
        """Prueba: distancia conocida entre Bogotá y Medellín."""
        # Bogotá: (4.7110, -74.0721)
        # Medellín: (6.2442, -75.5812)
        # Distancia en linea recta (haversine): ~239 km
        distance = haversine_calc(4.7110, -74.0721, 6.2442, -75.5812)
        self.assertGreater(distance, 220)
        self.assertLess(distance, 260)

    def test_is_within_radius_true(self):
        """Prueba: punto dentro del radio retorna True."""
        # Punto A: (4.7110, -74.0721)
        # Punto B: (4.7115, -74.0715) - muy cercano (~70 metros)
        result = is_within_radius(4.7110, -74.0721, 4.7115, -74.0715, max_radius_km=11)
        self.assertTrue(result)

    def test_is_within_radius_false(self):
        """Prueba: punto fuera del radio retorna False."""
        # Punto A: (4.7110, -74.0721)
        # Punto B: (6.2442, -75.5812) - ~376 km
        result = is_within_radius(4.7110, -74.0721, 6.2442, -75.5812, max_radius_km=11)
        self.assertFalse(result)

    def test_calculate_centroid(self):
        """Prueba: cálculo del centroide de puntos."""
        points = [
            (4.7110, -74.0721),
            (4.7115, -74.0715),
            (4.7105, -74.0725),
        ]
        centroid = calculate_centroid(points)
        self.assertAlmostEqual(centroid.lat, 4.7110, places=3)
        self.assertAlmostEqual(centroid.lng, -74.0720, places=3)

    def test_cluster_by_radius_all_within(self):
        """Prueba: clustering cuando todos están dentro del radio."""
        items = [
            {'id': 1, 'lat': 4.7110, 'lng': -74.0721},
            {'id': 2, 'lat': 4.7115, 'lng': -74.0715},
            {'id': 3, 'lat': 4.7105, 'lng': -74.0725},
        ]

        def get_coords(item):
            return (item['lat'], item['lng'])

        within, outside = cluster_by_radius(
            items, get_coords, 4.7110, -74.0721, max_radius_km=11
        )

        self.assertEqual(len(within), 3)
        self.assertEqual(len(outside), 0)

    def test_cluster_by_radius_some_outside(self):
        """Prueba: clustering con puntos dentro y fuera."""
        items = [
            {'id': 1, 'lat': 4.7110, 'lng': -74.0721},  # Centro
            {'id': 2, 'lat': 4.7115, 'lng': -74.0715},  # Cerca
            {'id': 3, 'lat': 6.2442, 'lng': -75.5812},  # Lejos (Medellín)
        ]

        def get_coords(item):
            return (item['lat'], item['lng'])

        within, outside = cluster_by_radius(
            items, get_coords, 4.7110, -74.0721, max_radius_km=11
        )

        self.assertEqual(len(within), 2)
        self.assertEqual(len(outside), 1)
        self.assertEqual(outside[0]['id'], 3)


class RouteOptimizerServiceTests(TestCase):
    """Pruebas del servicio de optimización de rutas."""

    def setUp(self):
        """Configuración inicial para todas las pruebas."""
        # Crear repartidor
        self.driver_user = CustomUser.objects.create_user(
            username='driver1',
            password='123',
            role='driver',
            nombre='Juan Pérez',
            estado='Disponible',
        )
        self.driver = Repartidor.objects.create(
            user=self.driver_user,
            latitud_actual=Decimal('4.7110'),
            longitud_actual=Decimal('-74.0721'),
            capacidad_maxima_kg=Decimal('20'),
        )

        # Crear bodega
        warehouse_user = CustomUser.objects.create_user(
            username='warehouse1',
            password='123',
            role='aliado',
            nombre='Bodega Central',
        )
        self.warehouse = Aliado.objects.create(
            user=warehouse_user,
            direccion='Carrera 5 #123',
            latitud=Decimal('4.7120'),
            longitud=Decimal('-74.0710'),
        )

        # Crear cliente y pedidos cercanos (dentro del radio ~11 km)
        self.cliente_cerca = Cliente.objects.create(
            nombre='Cliente A (Cerca)',
            direccion='Calle 80 #25',
            latitud=Decimal('4.7115'),
            longitud=Decimal('-74.0715'),
        )

        self.cliente_lejos = Cliente.objects.create(
            nombre='Cliente B (Lejos)',
            direccion='Medellín',
            latitud=Decimal('6.2442'),
            longitud=Decimal('-75.5812'),
        )

        # Crear pedidos
        self.pedido_cerca = Pedido.objects.create(
            cliente=self.cliente_cerca,
            estado='Pendiente',
            prioridad='normal',
            peso_total_kg=Decimal('5.0'),
        )

        self.pedido_lejos = Pedido.objects.create(
            cliente=self.cliente_lejos,
            estado='Pendiente',
            prioridad='normal',
            peso_total_kg=Decimal('5.0'),
        )

    def test_optimize_all_within_radius(self):
        """Prueba: optimización cuando todos los pedidos están dentro del radio."""
        optimizer = RouteOptimizerService()
        result = optimizer.optimize(
            repartidor_id=self.driver_user.id,
            latitud_inicial=4.7110,
            longitud_inicial=-74.0721,
            pedidos_candidatos=[self.pedido_cerca.id],
            capacidad_maxima=20,
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['total_rutas'], 1)
        self.assertEqual(len(result['pedidos_seleccionados']), 1)
        self.assertEqual(result['pedidos_seleccionados'][0].id, self.pedido_cerca.id)
        self.assertEqual(len(result['pedidos_descartados']), 0)

    def test_optimize_pedido_fuera_radio(self):
        """Prueba: pedido fuera del radio debe marcarse como descartado."""
        optimizer = RouteOptimizerService()
        result = optimizer.optimize(
            repartidor_id=self.driver_user.id,
            latitud_inicial=4.7110,
            longitud_inicial=-74.0721,
            pedidos_candidatos=[self.pedido_lejos.id],
            capacidad_maxima=20,
        )

        self.assertEqual(result['total_rutas'], 0)
        self.assertEqual(len(result['pedidos_seleccionados']), 0)
        self.assertGreater(len(result['pedidos_descartados']), 0)

        # Verificar que el motivo de descarte es sobre el radio
        discard_motivo = result['pedidos_descartados'][0].get('motivo', '')
        self.assertIn('radio máximo permitido', discard_motivo.lower())

    def test_optimize_radio_limit_respects_max_radius(self):
        """Prueba: el radio máximo se respeta correctamente."""
        optimizer = RouteOptimizerService()
        result = optimizer.optimize(
            repartidor_id=self.driver_user.id,
            latitud_inicial=4.7110,
            longitud_inicial=-74.0721,
            pedidos_candidatos=[self.pedido_cerca.id, self.pedido_lejos.id],
            capacidad_maxima=20,
        )

        # El pedido cercano debe estar seleccionado
        self.assertIn(self.pedido_cerca.id, [p.id for p in result['pedidos_seleccionados']])

        # El pedido lejano debe estar descartado
        descartes_ids = [d['pedido_id'] for d in result['pedidos_descartados']]
        self.assertIn(self.pedido_lejos.id, descartes_ids)

    def test_optimize_metrics_are_correct(self):
        """Prueba: las métricas retornadas son correctas."""
        optimizer = RouteOptimizerService()
        result = optimizer.optimize(
            repartidor_id=self.driver_user.id,
            latitud_inicial=4.7110,
            longitud_inicial=-74.0721,
            pedidos_candidatos=[self.pedido_cerca.id],
            capacidad_maxima=20,
        )

        metricas = result['metricas']
        self.assertEqual(metricas['total_pedidos_candidatos'], 1)
        self.assertEqual(metricas['pedidos_factibles'], 1)
        self.assertEqual(metricas['pedidos_dentro_radio'], 1)
        self.assertEqual(metricas['pedidos_fuera_radio'], 0)
        self.assertEqual(metricas['pedidos_seleccionados'], 1)

    def test_optimize_includes_radio_permitido(self):
        """Prueba: la respuesta incluye el radio permitido."""
        optimizer = RouteOptimizerService()
        result = optimizer.optimize(
            repartidor_id=self.driver_user.id,
            latitud_inicial=4.7110,
            longitud_inicial=-74.0721,
            pedidos_candidatos=[self.pedido_cerca.id],
            capacidad_maxima=20,
        )

        self.assertIn('radio_permitido_km', result)
        self.assertIn('radio_permitido_m2', result)
        self.assertAlmostEqual(result['radio_permitido_km'], MAX_ROUTE_RADIUS_KM, places=1)
        self.assertEqual(result['radio_permitido_m2'], MAX_ROUTE_AREA_KM2)

    def test_optimize_ruta_structure(self):
        """Prueba: la estructura de ruta es correcta."""
        optimizer = RouteOptimizerService()
        result = optimizer.optimize(
            repartidor_id=self.driver_user.id,
            latitud_inicial=4.7110,
            longitud_inicial=-74.0721,
            pedidos_candidatos=[self.pedido_cerca.id],
            capacidad_maxima=20,
        )

        self.assertIn('rutas', result)
        self.assertTrue(len(result['rutas']) > 0)

        ruta = result['rutas'][0]
        self.assertIn('repartidor_id', ruta)
        self.assertIn('pedidos_seleccionados', ruta)
        self.assertIn('orden_entrega', ruta)
        self.assertIn('distancia_total_km', ruta)
        self.assertIn('dentro_radio_permitido', ruta)


class AiRouteDecisionServiceTests(TestCase):
    """Pruebas del servicio IA de decisión."""

    def test_explain_with_empty_result(self):
        """Prueba: explicación cuando no hay rutas."""
        optimizer_result = {
            'rutas': [],
            'ruta_principal': None,
            'pedidos_seleccionados': [],
            'pedidos_descartados': [],
            'total_rutas': 0,
            'metricas': {
                'total_pedidos_candidatos': 0,
                'pedidos_seleccionados': 0,
                'pedidos_descartados': 0,
            }
        }

        service = AiRouteDecisionService()
        result = service.explain(optimizer_result)

        self.assertIn('alertas', result)
        self.assertIn('recomendaciones', result)
        self.assertIn('confianza', result)
        self.assertEqual(result['confianza']['nivel'], 'bajo')

    def test_explain_includes_radio_info(self):
        """Prueba: la explicación incluye información del radio."""
        optimizer_result = {
            'rutas': [{'repartidor_id': 1, 'pedidos_seleccionados': [1]}],
            'ruta_principal': {'repartidor_id': 1},
            'pedidos_seleccionados': [1],
            'pedidos_descartados': [
                {'pedido_id': 2, 'motivo': 'Fuera del radio máximo permitido de 11.03 km.'}
            ],
            'total_rutas': 1,
            'radio_permitido_km': MAX_ROUTE_RADIUS_KM,
            'radio_permitido_m2': MAX_ROUTE_AREA_KM2,
            'metricas': {
                'total_pedidos_candidatos': 2,
                'pedidos_dentro_radio': 1,
                'pedidos_fuera_radio': 1,
                'pedidos_seleccionados': 1,
            }
        }

        service = AiRouteDecisionService()
        result = service.explain(optimizer_result)

        # Debe incluir alertas sobre radio
        alertas_str = ' '.join(result['alertas'])
        self.assertIn('radio', alertas_str.lower())

        # Debe incluir información del radio en resultado
        self.assertIn('radio_permitido', result)
        self.assertAlmostEqual(result['radio_permitido']['km'], MAX_ROUTE_RADIUS_KM, places=1)

    def test_explain_confidence_high(self):
        """Prueba: confianza alta cuando la mayoría de pedidos son seleccionados."""
        optimizer_result = {
            'rutas': [{'pedidos_seleccionados': [1, 2, 3, 4]}],
            'ruta_principal': {'pedidos_seleccionados': [1, 2, 3, 4]},
            'pedidos_seleccionados': [1, 2, 3, 4],
            'pedidos_descartados': [],
            'total_rutas': 1,
            'metricas': {
                'total_pedidos_candidatos': 5,
                'pedidos_seleccionados': 4,
            }
        }

        service = AiRouteDecisionService()
        result = service.explain(optimizer_result)

        self.assertIn('confianza', result)
        self.assertEqual(result['confianza']['nivel'], 'alto')

    def test_explain_confidence_low(self):
        """Prueba: confianza baja cuando pocos pedidos son seleccionados."""
        optimizer_result = {
            'rutas': [{'pedidos_seleccionados': [1]}],
            'ruta_principal': {'pedidos_seleccionados': [1]},
            'pedidos_seleccionados': [1],
            'pedidos_descartados': [{'pedido_id': 2}, {'pedido_id': 3}],
            'total_rutas': 1,
            'metricas': {
                'total_pedidos_candidatos': 3,
                'pedidos_seleccionados': 1,
            }
        }

        service = AiRouteDecisionService()
        result = service.explain(optimizer_result)

        self.assertEqual(result['confianza']['nivel'], 'bajo')


class RadioMaximoCalculoTests(TestCase):
    """Pruebas del cálculo del radio máximo."""

    def test_radio_calculation_from_area(self):
        """Prueba: r = √(382/π) ≈ 11.03 km."""
        calculated_radius = math.sqrt(MAX_ROUTE_AREA_KM2 / math.pi)
        self.assertAlmostEqual(calculated_radius, MAX_ROUTE_RADIUS_KM, places=2)

    def test_radio_is_reasonable(self):
        """Prueba: el radio calculado es razonable para logística urbana."""
        # Debe estar entre 10 y 12 km para un área de 382 km²
        self.assertGreater(MAX_ROUTE_RADIUS_KM, 10)
        self.assertLess(MAX_ROUTE_RADIUS_KM, 12)

    def test_area_from_radius(self):
        """Prueba: A = π × r² reproduce el área original."""
        area_calculated = math.pi * (MAX_ROUTE_RADIUS_KM ** 2)
        self.assertAlmostEqual(area_calculated, MAX_ROUTE_AREA_KM2, places=1)


class EdgeCasesTests(TestCase):
    """Pruebas de casos extremos y validaciones."""

    def setUp(self):
        """Configuración para edge cases."""
        self.driver_user = CustomUser.objects.create_user(
            username='driver_edge',
            password='123',
            role='driver',
            nombre='Driver Edge',
            estado='Disponible',
        )
        self.driver = Repartidor.objects.create(
            user=self.driver_user,
            latitud_actual=Decimal('4.7110'),
            longitud_actual=Decimal('-74.0721'),
            capacidad_maxima_kg=Decimal('5'),  # Capacidad muy baja
        )

    def test_pedido_sin_coordenadas(self):
        """Prueba: pedido sin coordenadas se descarta."""
        cliente = Cliente.objects.create(
            nombre='Cliente Sin Coords',
            direccion='Dirección desconocida',
        )
        pedido = Pedido.objects.create(
            cliente=cliente,
            estado='Pendiente',
            prioridad='normal',
            peso_total_kg=Decimal('1'),
        )

        optimizer = RouteOptimizerService()
        result = optimizer.optimize(
            repartidor_id=self.driver_user.id,
            latitud_inicial=4.7110,
            longitud_inicial=-74.0721,
            pedidos_candidatos=[pedido.id],
            capacidad_maxima=10,
        )

        self.assertEqual(len(result['pedidos_seleccionados']), 0)
        self.assertGreater(len(result['pedidos_descartados']), 0)

    def test_pedido_peso_excede_capacidad(self):
        """Prueba: pedido que excede capacidad se descarta."""
        cliente = Cliente.objects.create(
            nombre='Cliente Peso Alto',
            direccion='Calle 50',
            latitud=Decimal('4.7115'),
            longitud=Decimal('-74.0715'),
        )
        pedido = Pedido.objects.create(
            cliente=cliente,
            estado='Pendiente',
            prioridad='normal',
            peso_total_kg=Decimal('10'),  # Más que la capacidad del driver (5)
        )

        optimizer = RouteOptimizerService()
        result = optimizer.optimize(
            repartidor_id=self.driver_user.id,
            latitud_inicial=4.7110,
            longitud_inicial=-74.0721,
            pedidos_candidatos=[pedido.id],
            capacidad_maxima=5,
        )

        self.assertEqual(len(result['pedidos_seleccionados']), 0)


# INSTRUCCIONES PARA EJECUTAR LAS PRUEBAS:
# python manage.py test logistics.tests.GeoSpatialHelpersTests
# python manage.py test logistics.tests.RouteOptimizerServiceTests
# python manage.py test logistics.tests.AiRouteDecisionServiceTests
# python manage.py test logistics.tests.RadioMaximoCalculoTests
# python manage.py test logistics.tests.EdgeCasesTests
# python manage.py test logistics.tests  # Ejecutar todas
