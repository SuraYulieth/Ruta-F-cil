from django.test import TestCase
from rest_framework.test import APIClient

from .models import Cliente, CustomUser, Pedido
from .services.route_optimizer_service import RouteOptimizerService, haversine_km


class RouteOptimizerServiceTests(TestCase):
    def setUp(self):
        self.driver = CustomUser.objects.create_user(
            username='driver1',
            password='123',
            role='driver',
            nombre='Driver Uno',
        )
        cliente_a = Cliente.objects.create(
            nombre='Cliente A',
            direccion='Zona A',
            latitud=4.7110,
            longitud=-74.0721,
        )
        cliente_b = Cliente.objects.create(
            nombre='Cliente B',
            direccion='Zona B',
            latitud=4.7150,
            longitud=-74.0750,
        )
        Cliente.objects.create(
            nombre='Sin coordenadas',
            direccion='Sin datos',
        )
        self.pedido_a = Pedido.objects.create(cliente=cliente_a, prioridad='alta', peso_total_kg=2)
        self.pedido_b = Pedido.objects.create(cliente=cliente_b, prioridad='normal', peso_total_kg=3)

    def test_haversine_returns_positive_distance(self):
        distance = haversine_km(4.7110, -74.0721, 4.7150, -74.0750)
        self.assertGreater(distance, 0)

    def test_optimizer_selects_feasible_orders(self):
        result = RouteOptimizerService().optimize(
            repartidor_id=self.driver.id,
            latitud_inicial=4.7100,
            longitud_inicial=-74.0700,
            capacidad_maxima=10,
        )

        selected_ids = [pedido.id for pedido in result['pedidos_seleccionados']]
        self.assertIn(self.pedido_a.id, selected_ids)
        self.assertIn(self.pedido_b.id, selected_ids)
        self.assertEqual(len(result['orden_entrega']), 2)
        self.assertGreater(result['distancia_total_km'], 0)


class RouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.driver = CustomUser.objects.create_user(
            username='driver-api',
            password='123',
            role='driver',
            nombre='Driver API',
        )
        cliente = Cliente.objects.create(
            nombre='Cliente API',
            direccion='Centro',
            latitud=4.7110,
            longitud=-74.0721,
        )
        self.pedido = Pedido.objects.create(cliente=cliente, prioridad='urgente', peso_total_kg=1)

    def test_optimize_route_endpoint_creates_route(self):
        response = self.client.post('/api/routes/optimize/', {
            'repartidor_id': self.driver.id,
            'latitud_inicial': 4.7100,
            'longitud_inicial': -74.0700,
            'pedidos_candidatos': [self.pedido.id],
            'capacidad_maxima': 5,
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['optimizer']['pedidos_seleccionados'], [self.pedido.id])
        self.assertEqual(len(response.data['route']['paradas']), 1)
