import os
import sys
import tempfile
import traceback
from pathlib import Path

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from django.db import transaction
from .models import CustomUser, Aliado, Repartidor, Cliente, Pedido, Ruta
from .serializers import (
    CustomUserSerializer, LoginSerializer, AliadoSerializer, 
    RepartidorSerializer, ClienteSerializer, PedidoSerializer, RutaSerializer,
    RouteOptimizeRequestSerializer, AssignPedidoRequestSerializer,
    PedidoDetailResponseSerializer, RepartidorInfoSerializer,
    DriverDetailSerializer, DriverLocationUpdateSerializer, DriverAvailabilitySerializer,
    DriverMyOrdersSerializer, DriverMyRoutesSerializer, OrderStateChangeSerializer
)
from .models import RutaParada
from .permissions import IsDriver, IsAdmin
from .services.ai_route_decision_service import AiRouteDecisionService
from .services.excel_import_service import import_excel_file
from .services.driver_visibility import (
    driver_visibility_reason,
    get_driver_coordinates,
    is_available_state,
    is_driver_available,
    is_driver_user,
)
from .services.route_metrics_service import RouteMetricsService
from .services.route_optimizer_service import RouteOptimizerService, to_decimal
from django.utils import timezone

BACKEND_DIR = Path(__file__).resolve().parents[1]
ASSIGN_DEBUG_LOG_PATH = BACKEND_DIR / 'assign_debug.log'


def _append_debug_log(message: str):
    try:
        ASSIGN_DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ASSIGN_DEBUG_LOG_PATH, 'a', encoding='utf-8') as debug_log:
            debug_log.write(message)
    except OSError:
        # No debemos fallar la petición por un problema de logging local.
        pass


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(username=username, password=password)
            if user:
                # Obtener o crear token
                token, created = Token.objects.get_or_create(user=user)
                
                # Preparar datos del usuario
                user_data = CustomUserSerializer(user).data
                # Adaptar campos para frontend
                user_data['name'] = user_data.pop('nombre', '')
                user_data['location'] = user_data.pop('ubicacion', 'Sin ubicación')
                user_data['status'] = user_data.pop('estado', 'Disponible')
                user_data['token'] = token.key
                
                # Si es repartidor, incluir info del Repartidor
                if is_driver_user(user):
                    try:
                        repartidor = Repartidor.objects.get(user=user)
                        user_data['repartidor_id'] = repartidor.id
                        user_data['disponible'] = repartidor.disponible
                    except Repartidor.DoesNotExist:
                        pass
                
                return Response(user_data, status=status.HTTP_200_OK)
            return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ImportExcelView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'Debe adjuntar un archivo en el campo file.'}, status=status.HTTP_400_BAD_REQUEST)

        extension = os.path.splitext(uploaded_file.name)[1].lower()
        if extension not in {'.xlsx', '.xls'}:
            return Response({'error': 'Formato no permitido. Use .xlsx o .xls.'}, status=status.HTTP_400_BAD_REQUEST)

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
                temp_path = temp_file.name
                for chunk in uploaded_file.chunks():
                    temp_file.write(chunk)

            result = import_excel_file(temp_path)
            response_status = status.HTTP_200_OK if not result.get('errors') else status.HTTP_207_MULTI_STATUS
            return Response(result, status=response_status)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        # Adaptar los datos para el mock del frontend (name, location, status)
        data = serializer.data
        for item in data:
            item['name'] = item.pop('nombre', '')
            item['location'] = item.pop('ubicacion', 'Sin ubicación')
            item['status'] = item.pop('estado', 'Disponible')
            if item.get('role') in ('driver', 'repartidor'):
                profile = Repartidor.objects.filter(user_id=item.get('id')).first()
                item['disponible'] = bool(profile and profile.disponible)
                if profile:
                    item['profile_id'] = profile.id
                    item['latitud_actual'] = profile.latitud_actual
                    item['longitud_actual'] = profile.longitud_actual
                    item['latitude'] = profile.latitud_actual
                    item['longitude'] = profile.longitud_actual
                    item['motivo_visibilidad'] = driver_visibility_reason(profile)
        return Response(data)

class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.select_related('cliente', 'aliado', 'repartidor').all()
    serializer_class = PedidoSerializer

    @action(detail=False, methods=['post'])
    def asignar_automatico(self, request):
        """
        Algoritmo de Análisis: Greedy Matching (Vecino más cercano)
        Complejidad: O(M * N)
        """
        pedidos_pendientes = Pedido.objects.filter(estado='Pendiente')
        repartidores_libres = [
            repartidor
            for repartidor in Repartidor.objects.select_related('user').all()
            if is_driver_available(repartidor)
        ]

        if not repartidores_libres or not pedidos_pendientes.exists():
            return Response(
                {"error": "No hay pedidos pendientes o repartidores disponibles"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        asignaciones = 0
        for pedido in pedidos_pendientes:
            if not repartidores_libres:
                break
            # Simulamos distancias (al no tener la lat/lon mapeada al 100% en todos lados por simplificacion)
            # En un entorno real se usaría Haversine. Aquí cogemos el primero disponible.
            mejor_repartidor = repartidores_libres[0]

            if mejor_repartidor:
                pedido.repartidor = mejor_repartidor.user
                pedido.estado = 'Asignado'
                pedido.save()
                
                # Ocupamos al repartidor para que no se le asignen multiples al mismo tiempo
                mejor_repartidor.user.estado = 'Ocupado'
                mejor_repartidor.user.save(update_fields=['estado'])
                repartidores_libres.pop(0)
                
                asignaciones += 1

        return Response({"mensaje": f"Se asignaron {asignaciones} pedidos exitosamente."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        """
        Asignación manual de un pedido individual a un repartidor.

        POST /api/pedidos/{id}/assign/
        Payload: {"repartidor_id": 3}
        """
        try:
            _append_debug_log('--- ASSIGN REQUEST ---\n')
            _append_debug_log(f'PK: {pk}\n')
            _append_debug_log(f'DATA: {request.data}\n')

            pedido = self.get_object()

            if pedido.estado == 'Entregado':
                return Response(
                    {'error': 'No se puede asignar un pedido entregado.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if pedido.estado == 'Cancelado':
                return Response(
                    {'error': 'No se puede asignar un pedido cancelado.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = AssignPedidoRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            repartidor_id = serializer.validated_data['repartidor_id']
            try:
                repartidor = CustomUser.objects.get(id=repartidor_id)
            except CustomUser.DoesNotExist:
                return Response(
                    {'error': 'El repartidor seleccionado no existe o no es un repartidor válido.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not is_driver_user(repartidor):
                return Response(
                    {'error': 'El repartidor seleccionado no existe o no es un repartidor valido.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            repartidor_profile = Repartidor.objects.filter(user=repartidor).first()
            if not is_driver_available(repartidor_profile):
                return Response(
                    {'error': 'Este repartidor esta deshabilitado y no puede recibir pedidos.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            es_reasignacion = pedido.repartidor is not None and pedido.estado == 'Asignado'
            pedido.repartidor = repartidor
            pedido.estado = 'Asignado'
            pedido.save(update_fields=['repartidor', 'estado'])

            if not pedido.paradas_ruta.exists():
                lat = pedido.cliente.latitud or 0
                lng = pedido.cliente.longitud or 0
                route = Ruta.objects.create(
                    pedido=pedido,
                    repartidor=repartidor,
                    aliado=pedido.aliado,
                    latitud_inicio=to_decimal(lat),
                    longitud_inicio=to_decimal(lng),
                    tiempo_estimado_mins=0,
                    distancia_km=0,
                    capacidad_usada_kg=pedido.peso_total_kg or 0,
                    estado_ruta='asignada',
                    geometria={
                        'type': 'LineString',
                        'coordinates': [[float(lng), float(lat)]],
                    },
                )
                RutaParada.objects.create(
                    ruta=route,
                    pedido=pedido,
                    orden=1,
                    latitud=to_decimal(lat),
                    longitud=to_decimal(lng),
                    distancia_desde_anterior_km=0,
                    tiempo_estimado_desde_anterior_mins=0,
                )

            response_data = PedidoDetailResponseSerializer(pedido).data
            return Response(
                {
                    'message': 'Pedido reasignado correctamente' if es_reasignacion else 'Pedido asignado correctamente',
                    'pedido': response_data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            _append_debug_log('ERROR:\n')
            _append_debug_log(''.join(traceback.format_exception(*sys.exc_info())))
            _append_debug_log('\n')
            raise

class RepartidorViewSet(viewsets.ModelViewSet):
    queryset = Repartidor.objects.all()
    serializer_class = RepartidorSerializer

    @action(detail=False, methods=['get'], url_path='diagnostics')
    def diagnostics(self, request):
        repartidores = list(Repartidor.objects.select_related('user').all())
        rows = []

        for repartidor in repartidores:
            coords = get_driver_coordinates(repartidor)
            user = repartidor.user
            rows.append({
                'id': repartidor.id,
                'user_id': repartidor.user_id,
                'nombre': user.nombre or user.username,
                'role': user.role,
                'estado': user.estado,
                'disponible': repartidor.disponible,
                'latitud_actual': repartidor.latitud_actual,
                'longitud_actual': repartidor.longitud_actual,
                'con_coordenadas': coords is not None,
                'motivo_no_visible': driver_visibility_reason(repartidor, require_coordinates=True),
            })

        return Response({
            'total_repartidores': len(repartidores),
            'con_role_driver': sum(1 for repartidor in repartidores if is_driver_user(repartidor.user)),
            'con_estado_disponible': sum(1 for repartidor in repartidores if is_available_state(repartidor.user.estado)),
            'con_disponible_true': sum(1 for repartidor in repartidores if repartidor.disponible is True),
            'con_coordenadas': sum(1 for repartidor in repartidores if get_driver_coordinates(repartidor) is not None),
            'repartidores': rows,
        })

class AliadoViewSet(viewsets.ModelViewSet):
    queryset = Aliado.objects.all()
    serializer_class = AliadoSerializer

class RutaViewSet(viewsets.ModelViewSet):
    queryset = Ruta.objects.select_related('repartidor', 'pedido').prefetch_related('paradas__pedido__cliente').all()
    serializer_class = RutaSerializer
    permission_classes = []  # Permitir acceso sin autenticación, pero los métodos puede validar

    @action(detail=False, methods=['post'], url_path='optimize', permission_classes=[])
    def optimize(self, request):
        request_serializer = RouteOptimizeRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        data = request_serializer.validated_data
        mode = data.get('modo', 'ruta_unica')

        optimizer = RouteOptimizerService()
        if mode == 'multi_ruta':
            result = optimizer.optimize_all_pending_orders(
                repartidor_id=data.get('repartidor_id'),
                latitud_inicial=data.get('latitud_inicial'),
                longitud_inicial=data.get('longitud_inicial'),
                pedidos_candidatos=data.get('pedidos_candidatos'),
                capacidad_maxima=data.get('capacidad_maxima'),
                reglas_negocio=data.get('reglas_negocio'),
                max_duration_mins=data.get('max_duration_mins'),
                max_area_km2=data.get('max_area_km2'),
                max_distance_km=data.get('max_distance_km'),
            )
        else:
            result = optimizer.optimize(
                repartidor_id=data.get('repartidor_id'),
                latitud_inicial=data.get('latitud_inicial'),
                longitud_inicial=data.get('longitud_inicial'),
                pedidos_candidatos=data.get('pedidos_candidatos'),
                capacidad_maxima=data.get('capacidad_maxima'),
                reglas_negocio=data.get('reglas_negocio'),
            )

        decision = AiRouteDecisionService().explain(result)
        metrics = RouteMetricsService().build(result)

        if mode == 'multi_ruta':
            if not result.get('routes'):
                return Response(
                    {
                        'route': None,
                        'routes': [],
                        'unassigned_orders': result.get('unassigned_orders', []),
                        'summary': result.get('summary', {}),
                        'decision': decision,
                        'metrics': metrics,
                        'optimizer': self._serialize_optimizer_result(result),
                    },
                    status=status.HTTP_200_OK,
                )

            created_routes = []
            with transaction.atomic():
                for plan in result['routes']:
                    created_routes.append(self._create_route_from_plan(plan, decision, metrics))

            return Response(
                {
                    'route': created_routes[0] if created_routes else None,
                    'routes': created_routes,
                    'unassigned_orders': result.get('unassigned_orders', []),
                    'summary': result.get('summary', {}),
                    'decision': decision,
                    'metrics': metrics,
                    'optimizer': self._serialize_optimizer_result(result),
                },
                status=status.HTTP_201_CREATED,
            )

        if not result['pedidos_seleccionados']:
            return Response(
                {
                    'route': None,
                    'routes': [],
                    'decision': decision,
                    'metrics': metrics,
                    'optimizer': self._serialize_optimizer_result(result),
                },
                status=status.HTTP_200_OK,
            )

        route = self._create_route_from_plan(result, decision, metrics)

        return Response(
            {
                'route': route,
                'routes': [route],
                'decision': decision,
                'metrics': metrics,
                'optimizer': self._serialize_optimizer_result(result),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='evidence')
    def evidence(self, request, pk=None):
        route = self.get_object()
        decision = route.decision_ai or {}
        return Response({
            'ruta_id': route.id,
            'distancia_total_km': route.distancia_km,
            'tiempo_estimado_mins': route.tiempo_estimado_mins,
            'capacidad_usada_kg': route.capacidad_usada_kg,
            'bodega_seleccionada': route.aliado.user.nombre if route.aliado else None,
            'repartidor_seleccionado': route.repartidor.nombre,
            'pedidos_asignados': list(route.paradas.values_list('pedido_id', flat=True)),
            'explicacion_ia': decision.get('explicacion'),
            'metrics': decision.get('metrics'),
        })

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        route = self.get_object()
        if not route.repartidor:
            return Response(
                {'error': 'La ruta no tiene repartidor asignado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        repartidor_profile = Repartidor.objects.filter(user=route.repartidor).first()
        if not is_driver_available(repartidor_profile):
            return Response(
                {'error': 'Este repartidor esta deshabilitado y no puede recibir pedidos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order_ids = list(route.paradas.values_list('pedido_id', flat=True))
        if not order_ids:
            return Response(
                {'error': 'La ruta no tiene paradas registradas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            Pedido.objects.filter(id__in=order_ids).update(
                repartidor=route.repartidor,
                estado='Asignado',
            )
            route.paradas.update(estado='pendiente')
            route.estado_ruta = 'asignada'
            route.save(update_fields=['estado_ruta'])
            route.repartidor.estado = 'Ocupado'
            route.repartidor.save(update_fields=['estado'])

        return Response(RutaSerializer(route).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        route = self.get_object()
        next_status = request.data.get('estado_ruta')
        if not next_status:
            return Response(
                {'error': 'Debe enviar el campo estado_ruta.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_statuses = {choice[0] for choice in Ruta._meta.get_field('estado_ruta').choices}
        if next_status not in valid_statuses:
            return Response(
                {'error': f'estado_ruta inválido. Use uno de: {sorted(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        route.estado_ruta = next_status
        route.save(update_fields=['estado_ruta'])

        if next_status == 'en_ruta':
            order_ids = list(route.paradas.values_list('pedido_id', flat=True))
            route.paradas.update(estado='pendiente')
            Pedido.objects.filter(id__in=order_ids).update(estado='En ruta')
        elif next_status == 'completada':
            order_ids = list(route.paradas.values_list('pedido_id', flat=True))
            Pedido.objects.filter(id__in=order_ids).update(estado='Entregado')
            route.repartidor.estado = 'Disponible'
            route.repartidor.save(update_fields=['estado'])

        return Response(RutaSerializer(route).data, status=status.HTTP_200_OK)

    def _create_route_from_plan(self, plan, decision, metrics):
        repartidor = CustomUser.objects.filter(id=plan['repartidor_id']).first()
        if repartidor and not is_driver_user(repartidor):
            repartidor = None
        if not repartidor:
            raise ValueError('No hay repartidor viable para la ruta optimizada.')

        aliado = Aliado.objects.filter(id=plan.get('aliado_id')).first()
        selected_orders = plan.get('pedidos_seleccionados', [])
        primary_order = selected_orders[0] if selected_orders else None

        route = Ruta.objects.create(
            pedido=primary_order,
            repartidor=repartidor,
            aliado=aliado,
            latitud_inicio=to_decimal(plan['start']['lat']),
            longitud_inicio=to_decimal(plan['start']['lng']),
            tiempo_estimado_mins=plan['duracion_total_mins'],
            distancia_km=plan['distancia_total_km'],
            capacidad_usada_kg=plan['capacidad_usada_kg'],
            estado_ruta='asignada',
            geometria=plan.get('geometria'),
            decision_ai={
                **decision,
                'metrics': metrics,
                'route_summary': {
                    'repartidor_id': plan.get('repartidor_id'),
                    'pedidos_seleccionados': [pedido.id for pedido in selected_orders],
                    'distancia_total_km': plan.get('distancia_total_km'),
                    'duracion_total_mins': plan.get('duracion_total_mins'),
                },
            },
        )

        for index, stop in enumerate(plan['orden_entrega'], start=1):
            pedido = stop['pedido']
            if pedido.aliado_id:
                pedido.save(update_fields=['aliado'])
            pedido.repartidor = repartidor
            pedido.estado = 'Asignado'
            pedido.save(update_fields=['repartidor', 'estado'])
            RutaParada.objects.create(
                ruta=route,
                pedido=pedido,
                orden=index,
                latitud=to_decimal(stop['lat']),
                longitud=to_decimal(stop['lng']),
                distancia_desde_anterior_km=stop['distancia_desde_anterior_km'],
                tiempo_estimado_desde_anterior_mins=stop['tiempo_estimado_desde_anterior_mins'],
            )

        repartidor.estado = 'Ocupado'
        repartidor.save(update_fields=['estado'])

        return RutaSerializer(route).data

    def _serialize_route_plan(self, plan):
        pedidos_seleccionados = plan.get('pedidos_seleccionados', [])
        orden_entrega = plan.get('orden_entrega', [])
        return {
            'repartidor_id': plan.get('repartidor_id'),
            'repartidor_nombre': plan.get('repartidor_nombre'),
            'repartidor_motivo': plan.get('repartidor_motivo'),
            'aliado_id': plan.get('aliado_id'),
            'aliado_nombre': plan.get('aliado_nombre'),
            'start': plan.get('start'),
            'pedidos_seleccionados': [pedido.id for pedido in pedidos_seleccionados],
            'orden_entrega': [
                {
                    'pedido_id': stop['pedido'].id,
                    'orden': index,
                    'lat': stop['lat'],
                    'lng': stop['lng'],
                    'distancia_desde_anterior_km': stop['distancia_desde_anterior_km'],
                    'tiempo_estimado_desde_anterior_mins': stop['tiempo_estimado_desde_anterior_mins'],
                }
                for index, stop in enumerate(orden_entrega, start=1)
            ],
            'distancia_total_km': plan.get('distancia_total_km'),
            'duracion_total_mins': plan.get('duracion_total_mins'),
            'capacidad_usada_kg': plan.get('capacidad_usada_kg'),
            'geometria': plan.get('geometria'),
            'radio_permitido_km': plan.get('radio_permitido_km'),
            'radio_permitido_m2': plan.get('radio_permitido_m2'),
            'dentro_radio_permitido': plan.get('dentro_radio_permitido'),
            'max_duration_mins': plan.get('max_duration_mins'),
            'max_distance_km': plan.get('max_distance_km'),
            'scoring': plan.get('scoring', []),
            'pedidos_descartados_por_scoring': plan.get('pedidos_descartados_por_scoring', []),
        }

    def _serialize_optimizer_result(self, result):
        if result.get('routes'):
            routes = [self._serialize_route_plan(route) for route in result.get('routes', [])]
            route_principal = routes[0] if routes else None
            pedidos_seleccionados = [pedido_id for route in routes for pedido_id in route['pedidos_seleccionados']]
            return {
                'modo': result.get('modo', 'multi_ruta'),
                'routes': routes,
                'route': route_principal,
                'ruta_principal': route_principal,
                'unassigned_orders': result.get('unassigned_orders', []),
                'pedidos_seleccionados': pedidos_seleccionados,
                'pedidos_descartados': result.get('pedidos_descartados', []),
                'distancia_total_km': result.get('distancia_total_km'),
                'duracion_total_mins': result.get('duracion_total_mins'),
                'capacidad_total_usada_kg': result.get('capacidad_total_usada_kg'),
                'summary': result.get('summary', {}),
                'radio_permitido_km': result.get('radio_permitido_km'),
                'radio_permitido_m2': result.get('radio_permitido_m2'),
                'explicacion': result.get('explicacion'),
            }

        if result.get('modo') == 'multi_ruta':
            return {
                'modo': 'multi_ruta',
                'routes': [],
                'route': None,
                'ruta_principal': None,
                'unassigned_orders': result.get('unassigned_orders', []),
                'pedidos_seleccionados': [],
                'pedidos_descartados': result.get('pedidos_descartados', []),
                'distancia_total_km': result.get('distancia_total_km', 0),
                'duracion_total_mins': result.get('duracion_total_mins', 0),
                'capacidad_total_usada_kg': result.get('capacidad_total_usada_kg', 0),
                'summary': result.get('summary', {}),
                'radio_permitido_km': result.get('radio_permitido_km'),
                'radio_permitido_m2': result.get('radio_permitido_m2'),
                'explicacion': result.get('explicacion'),
            }

        return {
            'pedidos_seleccionados': [pedido.id for pedido in result['pedidos_seleccionados']],
            'orden_entrega': [
                {
                    'pedido_id': stop['pedido'].id,
                    'orden': index,
                    'lat': stop['lat'],
                    'lng': stop['lng'],
                    'distancia_desde_anterior_km': stop['distancia_desde_anterior_km'],
                    'tiempo_estimado_desde_anterior_mins': stop['tiempo_estimado_desde_anterior_mins'],
                }
                for index, stop in enumerate(result['orden_entrega'], start=1)
            ],
            'pedidos_descartados': result['pedidos_descartados'],
            'distancia_total_km': result['distancia_total_km'],
            'duracion_total_mins': result['duracion_total_mins'],
            'capacidad_usada_kg': result['capacidad_usada_kg'],
            'repartidor_id': result.get('repartidor_id'),
            'repartidor_nombre': result.get('repartidor_nombre'),
            'repartidor_motivo': result.get('repartidor_motivo'),
            'aliado_id': result.get('aliado_id'),
            'aliado_nombre': result.get('aliado_nombre'),
            'scoring': result.get('scoring', []),
            'geometria': result['geometria'],
            'explicacion': result['explicacion'],
        }


# ============================================================================
# DRIVER VIEWSET - ENDPOINTS ESPECÍFICOS PARA REPARTIDORES
# ============================================================================

class DriverViewSet(viewsets.ViewSet):
    """
    API endpoints específicos para repartidores.
    Endpoints:
    - GET /api/drivers/me/ - Info del driver autenticado
    - POST /api/drivers/me/toggle-availability/ - Cambiar disponibilidad
    - GET /api/drivers/me/orders/ - Pedidos asignados
    - GET /api/drivers/me/routes/ - Rutas del driver
    - POST /api/drivers/me/location/ - Actualizar ubicación
    - POST /api/orders/{id}/start/ - Cambiar a "En ruta"
    - POST /api/orders/{id}/deliver/ - Cambiar a "Entregado"
    - POST /api/orders/{id}/complete/ - Completar pedido
    """
    permission_classes = [IsAuthenticated, IsDriver]
    no_profile_message = 'Este usuario no tiene perfil de repartidor asociado.'

    def list(self, request):
        """Redirige a /drivers/me/"""
        return self.me(request)

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Obtener información del repartidor autenticado."""
        try:
            repartidor = Repartidor.objects.get(user=request.user)
            repartidor.ultima_conexion = timezone.now()
            repartidor.save(update_fields=['ultima_conexion'])
            serializer = DriverDetailSerializer(repartidor)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Repartidor.DoesNotExist:
            return Response(
                {"error": self.no_profile_message},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='me/toggle-availability')
    def toggle_availability(self, request):
        """Cambiar disponibilidad del repartidor."""
        try:
            repartidor = Repartidor.objects.get(user=request.user)
            serializer = DriverAvailabilitySerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            disponible = serializer.validated_data['disponible']
            repartidor.disponible = disponible
            repartidor.ultima_conexion = timezone.now()
            repartidor.save(update_fields=['disponible', 'ultima_conexion'])
            
            # Actualizar estado en CustomUser también
            repartidor.user.estado = 'Disponible' if disponible else 'No disponible'
            repartidor.user.save(update_fields=['estado'])
            
            message = "Ahora estás disponible para recibir pedidos." if disponible else "Ahora estás no disponible."
            return Response(
                {
                    "available": disponible,
                    "message": message,
                    "disponible": disponible,
                    "mensaje": message,
                    "repartidor": DriverDetailSerializer(repartidor).data
                },
                status=status.HTTP_200_OK
            )
        except Repartidor.DoesNotExist:
            return Response(
                {"error": self.no_profile_message},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='me/orders')
    def my_orders(self, request):
        """Listar pedidos asignados al repartidor."""
        try:
            repartidor = Repartidor.objects.get(user=request.user)
            
            # Filtrar por estado si viene en query params
            estado = request.query_params.get('estado')
            orders_query = Pedido.objects.filter(repartidor=request.user).select_related('cliente')
            
            if estado:
                orders_query = orders_query.filter(estado=estado)
            
            orders_query = orders_query.order_by('-fecha_creacion')
            serializer = DriverMyOrdersSerializer(orders_query, many=True)
            
            # Actualizar última conexión
            repartidor.ultima_conexion = timezone.now()
            repartidor.save(update_fields=['ultima_conexion'])
            
            return Response(
                {
                    "total": orders_query.count(),
                    "pedidos": serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Repartidor.DoesNotExist:
            return Response(
                {"error": self.no_profile_message},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='me/routes')
    def my_routes(self, request):
        """Listar rutas asignadas al repartidor."""
        try:
            repartidor = Repartidor.objects.get(user=request.user)
            
            # Filtrar por estado si viene en query params
            estado_ruta = request.query_params.get('estado_ruta')
            routes_query = Ruta.objects.filter(repartidor=request.user).prefetch_related('paradas__pedido__cliente')
            
            if estado_ruta:
                routes_query = routes_query.filter(estado_ruta=estado_ruta)
            
            routes_query = routes_query.order_by('-fecha_creacion')
            serializer = DriverMyRoutesSerializer(routes_query, many=True)
            
            # Actualizar última conexión
            repartidor.ultima_conexion = timezone.now()
            repartidor.save(update_fields=['ultima_conexion'])
            
            return Response(
                {
                    "total": routes_query.count(),
                    "rutas": serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Repartidor.DoesNotExist:
            return Response(
                {"error": self.no_profile_message},
                status=status.HTTP_404_NOT_FOUND
            )

    def _sync_route_after_stop_update(self, order):
        stops = RutaParada.objects.select_related('ruta').filter(pedido=order)
        for stop in stops:
            route = stop.ruta
            route_stops = route.paradas.all()
            if route_stops.exists() and not route_stops.exclude(estado='completada').exists():
                route.estado_ruta = 'completada'
                route.save(update_fields=['estado_ruta'])
                if not Pedido.objects.filter(
                    repartidor=route.repartidor,
                    estado__in=['Asignado', 'En ruta'],
                ).exists():
                    route.repartidor.estado = 'Disponible'
                    route.repartidor.save(update_fields=['estado'])

    @action(detail=False, methods=['post'], url_path='me/location')
    def update_location(self, request):
        """Actualizar ubicación del repartidor."""
        try:
            repartidor = Repartidor.objects.get(user=request.user)
            serializer = DriverLocationUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            lat = serializer.validated_data['latitud']
            lng = serializer.validated_data['longitud']
            
            repartidor.latitud_actual = lat
            repartidor.longitud_actual = lng
            repartidor.ultima_ubicacion = {
                'latitud': float(lat),
                'longitud': float(lng),
                'timestamp': timezone.now().isoformat()
            }
            repartidor.ultima_conexion = timezone.now()
            repartidor.save(update_fields=['latitud_actual', 'longitud_actual', 'ultima_ubicacion', 'ultima_conexion'])
            
            return Response(
                {
                    "mensaje": "Ubicación actualizada correctamente",
                    "repartidor": DriverDetailSerializer(repartidor).data
                },
                status=status.HTTP_200_OK
            )
        except Repartidor.DoesNotExist:
            return Response(
                {"error": self.no_profile_message},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='me/orders/(?P<order_id>[0-9]+)/start')
    def order_start(self, request, order_id=None):
        """Cambiar estado de pedido a 'En ruta'."""
        try:
            order = Pedido.objects.get(id=order_id, repartidor=request.user)
            
            if order.estado == 'En ruta':
                return Response(
                    {"mensaje": "El pedido ya está en ruta"},
                    status=status.HTTP_200_OK
                )
            
            order.estado = 'En ruta'
            order.save(update_fields=['estado'])
            
            # Actualizar parada si existe
            RutaParada.objects.filter(pedido=order).update(estado='pendiente')
            Ruta.objects.filter(paradas__pedido=order, estado_ruta='asignada').update(estado_ruta='en_ruta')
            
            return Response(
                {
                    "mensaje": "Pedido actualizado a 'En ruta'",
                    "pedido": DriverMyOrdersSerializer(order).data
                },
                status=status.HTTP_200_OK
            )
        except Pedido.DoesNotExist:
            return Response(
                {"error": "Pedido no encontrado o no asignado a ti"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='me/orders/(?P<order_id>[0-9]+)/deliver')
    def order_deliver(self, request, order_id=None):
        """Cambiar estado de pedido a 'Entregado'."""
        try:
            order = Pedido.objects.get(id=order_id, repartidor=request.user)
            
            if order.estado == 'Entregado':
                return Response(
                    {"mensaje": "El pedido ya fue entregado"},
                    status=status.HTTP_200_OK
                )
            
            order.estado = 'Entregado'
            order.fecha_entrega = timezone.now()
            order.save(update_fields=['estado', 'fecha_entrega'])
            
            # Actualizar parada si existe
            RutaParada.objects.filter(pedido=order).update(estado='completada')
            self._sync_route_after_stop_update(order)
            
            return Response(
                {
                    "mensaje": "Pedido entregado exitosamente",
                    "pedido": DriverMyOrdersSerializer(order).data
                },
                status=status.HTTP_200_OK
            )
        except Pedido.DoesNotExist:
            return Response(
                {"error": "Pedido no encontrado o no asignado a ti"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'], url_path='me/orders/(?P<order_id>[0-9]+)/complete')
    def order_complete(self, request, order_id=None):
        """Completar pedido (equivalente operativo a entrega final)."""
        try:
            order = Pedido.objects.get(id=order_id, repartidor=request.user)

            if order.estado == 'Entregado':
                return Response(
                    {"mensaje": "El pedido ya fue completado"},
                    status=status.HTTP_200_OK
                )

            order.estado = 'Entregado'
            order.fecha_entrega = timezone.now()
            order.save(update_fields=['estado', 'fecha_entrega'])
            RutaParada.objects.filter(pedido=order).update(estado='completada')
            self._sync_route_after_stop_update(order)

            return Response(
                {
                    "mensaje": "Pedido completado exitosamente",
                    "pedido": DriverMyOrdersSerializer(order).data,
                },
                status=status.HTTP_200_OK,
            )
        except Pedido.DoesNotExist:
            return Response(
                {"error": "Pedido no encontrado o no asignado a ti"},
                status=status.HTTP_404_NOT_FOUND,
            )
