from django.test import TestCase
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import skipIf

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

from .models import Aliado, Cliente, CustomUser, Pedido, Repartidor
from .services.route_metrics_service import RouteMetricsService
from .services.route_optimizer_service import RouteOptimizerService, haversine_km


class RouteOptimizerServiceTests(TestCase):
    def setUp(self):
        self.driver = CustomUser.objects.create_user(
            username='driver1',
            password='123',
            role='driver',
            nombre='Driver Uno',
        )
        Repartidor.objects.create(
            user=self.driver,
            latitud_actual=4.7100,
            longitud_actual=-74.0700,
            capacidad_maxima_kg=10,
        )
        warehouse_user = CustomUser.objects.create_user(
            username='warehouse1',
            password='123',
            role='aliado',
            nombre='Bodega Test',
        )
        self.warehouse = Aliado.objects.create(
            user=warehouse_user,
            direccion='Bodega',
            latitud=4.7120,
            longitud=-74.0710,
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
        self.assertEqual(result['aliado_id'], self.warehouse.id)

    def test_optimizer_can_select_driver_automatically(self):
        result = RouteOptimizerService().optimize(capacidad_maxima=10)
        self.assertEqual(result['repartidor_id'], self.driver.id)


class RouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.driver = CustomUser.objects.create_user(
            username='driver-api',
            password='123',
            role='driver',
            nombre='Driver API',
        )
        Repartidor.objects.create(
            user=self.driver,
            latitud_actual=4.7100,
            longitud_actual=-74.0700,
            capacidad_maxima_kg=5,
        )
        warehouse_user = CustomUser.objects.create_user(
            username='warehouse-api',
            password='123',
            role='aliado',
            nombre='Bodega API',
        )
        Aliado.objects.create(
            user=warehouse_user,
            direccion='Centro',
            latitud=4.7115,
            longitud=-74.0715,
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
        self.assertIn('metrics', response.data)


class RouteMetricsServiceTests(TestCase):
    def test_build_returns_abp_evidence(self):
        result = {
            'pedidos_seleccionados': [],
            'distancia_total_km': 10,
            'duracion_total_mins': 30,
            'capacidad_usada_kg': 5,
            'aliado_nombre': 'Bodega',
            'repartidor_nombre': 'Driver',
            'explicacion': 'Decision explicada',
        }
        metrics = RouteMetricsService().build(result)
        self.assertEqual(metrics['complejidad']['caso_promedio'], 'O(n^2)')
        self.assertEqual(metrics['comparacion_manual_excel']['distancia_sistema_km'], 10)


@skipIf(Workbook is None, 'openpyxl no esta instalado')
class ImportExcelCommandTests(TestCase):
    def test_import_excel_command_loads_core_entities(self):
        workbook = Workbook()
        aliados = workbook.active
        aliados.title = 'Aliados'
        aliados.append(['nombre', 'username', 'direccion', 'latitud', 'longitud'])
        aliados.append(['Bodega Uno', 'bodega_uno', 'Centro', 4.71, -74.07])

        repartidores = workbook.create_sheet('Repartidores')
        repartidores.append(['nombre', 'username', 'estado', 'latitud', 'longitud', 'capacidad'])
        repartidores.append(['Driver Uno', 'driver_uno', 'Disponible', 4.72, -74.08, 12])

        pedidos = workbook.create_sheet('Pedidos')
        pedidos.append(['cliente', 'direccion', 'latitud', 'longitud', 'prioridad', 'peso', 'bodega'])
        pedidos.append(['Cliente Uno', 'Calle 1', 4.73, -74.09, 'alta', 2, 'Bodega Uno'])

        with TemporaryDirectory() as directory:
            file_path = Path(directory) / 'import.xlsx'
            workbook.save(file_path)
            call_command('import_excel', str(file_path))

        self.assertEqual(Aliado.objects.count(), 1)
        self.assertEqual(Repartidor.objects.count(), 1)
        self.assertEqual(Cliente.objects.count(), 1)
        self.assertEqual(Pedido.objects.count(), 1)

    def test_import_excel_endpoint_accepts_multipart_file(self):
        workbook = Workbook()
        clientes = workbook.active
        clientes.title = 'Clientes'
        clientes.append(['nombre', 'direccion', 'latitud', 'longitud'])
        clientes.append(['Cliente API Excel', 'Calle 2', 4.71, -74.07])

        with TemporaryDirectory() as directory:
            file_path = Path(directory) / 'import.xlsx'
            workbook.save(file_path)
            upload = SimpleUploadedFile(
                'import.xlsx',
                file_path.read_bytes(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )

        response = APIClient().post('/api/import-excel/', {'file': upload}, format='multipart')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['created']['clientes'], 1)
        self.assertEqual(Cliente.objects.count(), 1)

    def test_import_excel_endpoint_requires_file(self):
        response = APIClient().post('/api/import-excel/', {}, format='multipart')

        self.assertEqual(response.status_code, 400)
