import os
import tempfile

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from django.db import transaction
from .models import CustomUser, Aliado, Repartidor, Cliente, Pedido, Ruta
from .serializers import (
    CustomUserSerializer, LoginSerializer, AliadoSerializer, 
    RepartidorSerializer, ClienteSerializer, PedidoSerializer, RutaSerializer,
    RouteOptimizeRequestSerializer
)
from .models import RutaParada
from .services.ai_route_decision_service import AiRouteDecisionService
from .services.excel_import_service import import_excel_file
from .services.route_metrics_service import RouteMetricsService
from .services.route_optimizer_service import RouteOptimizerService, to_decimal

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(username=username, password=password)
            if user:
                # Retornamos el objeto user tal como lo espera el frontend
                user_data = CustomUserSerializer(user).data
                # Frontend necesita 'name' en lugar de 'nombre'
                user_data['name'] = user_data.pop('nombre', '')
                user_data['location'] = user_data.pop('ubicacion', 'Sin ubicación')
                user_data['status'] = user_data.pop('estado', 'Disponible')
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
        repartidores_libres = CustomUser.objects.filter(role='driver', estado='Disponible')

        if not repartidores_libres.exists() or not pedidos_pendientes.exists():
            return Response(
                {"error": "No hay pedidos pendientes o repartidores disponibles"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        asignaciones = 0
        for pedido in pedidos_pendientes:
            mejor_repartidor = None
            
            # Simulamos distancias (al no tener la lat/lon mapeada al 100% en todos lados por simplificacion)
            # En un entorno real se usaría Haversine. Aquí cogemos el primero disponible.
            mejor_repartidor = repartidores_libres.first()

            if mejor_repartidor:
                pedido.repartidor = mejor_repartidor
                pedido.estado = 'Asignado'
                pedido.save()
                
                # Ocupamos al repartidor para que no se le asignen multiples al mismo tiempo
                mejor_repartidor.estado = 'Ocupado'
                mejor_repartidor.save()
                
                asignaciones += 1

        return Response({"mensaje": f"Se asignaron {asignaciones} pedidos exitosamente."}, status=status.HTTP_200_OK)

class RepartidorViewSet(viewsets.ModelViewSet):
    queryset = Repartidor.objects.all()
    serializer_class = RepartidorSerializer

class AliadoViewSet(viewsets.ModelViewSet):
    queryset = Aliado.objects.all()
    serializer_class = AliadoSerializer

class RutaViewSet(viewsets.ModelViewSet):
    queryset = Ruta.objects.select_related('repartidor', 'pedido').prefetch_related('paradas__pedido__cliente').all()
    serializer_class = RutaSerializer

    @action(detail=False, methods=['post'], url_path='optimize')
    def optimize(self, request):
        request_serializer = RouteOptimizeRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        data = request_serializer.validated_data

        optimizer = RouteOptimizerService()
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

        if not result['pedidos_seleccionados']:
            return Response(
                {
                    'route': None,
                    'decision': decision,
                    'metrics': metrics,
                    'optimizer': self._serialize_optimizer_result(result),
                },
                status=status.HTTP_200_OK,
            )

        repartidor = CustomUser.objects.filter(id=result['repartidor_id'], role='driver').first()
        if not repartidor:
            return Response(
                {'error': 'No hay repartidor viable para la ruta optimizada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        aliado = Aliado.objects.filter(id=result.get('aliado_id')).first()

        with transaction.atomic():
            route = Ruta.objects.create(
                repartidor=repartidor,
                aliado=aliado,
                latitud_inicio=to_decimal(result['start']['lat']),
                longitud_inicio=to_decimal(result['start']['lng']),
                tiempo_estimado_mins=result['duracion_total_mins'],
                distancia_km=result['distancia_total_km'],
                capacidad_usada_kg=result['capacidad_usada_kg'],
                geometria=result['geometria'],
                decision_ai={**decision, 'metrics': metrics},
            )
            for index, stop in enumerate(result['orden_entrega'], start=1):
                if stop['pedido'].aliado_id:
                    stop['pedido'].save(update_fields=['aliado'])
                RutaParada.objects.create(
                    ruta=route,
                    pedido=stop['pedido'],
                    orden=index,
                    latitud=to_decimal(stop['lat']),
                    longitud=to_decimal(stop['lng']),
                    distancia_desde_anterior_km=stop['distancia_desde_anterior_km'],
                    tiempo_estimado_desde_anterior_mins=stop['tiempo_estimado_desde_anterior_mins'],
                )

        return Response(
            {
                'route': RutaSerializer(route).data,
                'decision': decision,
                'metrics': metrics,
                'optimizer': self._serialize_optimizer_result(result),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path='optimize-batch')
    def optimize_batch(self, request):
        """
        Algoritmo de Optimización en Lote (Batch Routing)
        Complejidad: O(K * M log M) donde K es el número de conductores y M el de pedidos.
        """
        drivers = CustomUser.objects.filter(role='driver', estado='Disponible')
        pending_orders = Pedido.objects.filter(estado='Pendiente')

        if not drivers.exists():
            return Response(
                {"error": "No hay repartidores disponibles para realizar la optimización en lote."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not pending_orders.exists():
            return Response(
                {"error": "No hay pedidos pendientes para optimizar."},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_routes = []
        remaining_order_ids = list(pending_orders.values_list('id', flat=True))
        optimizer = RouteOptimizerService()

        # Iterar sobre los conductores disponibles
        for driver in drivers:
            if not remaining_order_ids:
                break

            # Obtener ubicación inicial del conductor
            profile = Repartidor.objects.filter(user=driver).first()
            lat_init = float(profile.latitud_actual) if profile and profile.latitud_actual is not None else 4.7110
            lng_init = float(profile.longitud_actual) if profile and profile.longitud_actual is not None else -74.0721

            # Ejecutar optimización individual con el conjunto restante de pedidos
            result = optimizer.optimize(
                repartidor_id=driver.id,
                latitud_inicial=lat_init,
                longitud_inicial=lng_init,
                pedidos_candidatos=remaining_order_ids,
                capacidad_maxima=float(profile.capacidad_maxima_kg) if profile else 15.0,
                reglas_negocio={'max_orders': 6}
            )

            # Si no se seleccionó ningún pedido para este conductor, continuamos con el siguiente
            if not result['pedidos_seleccionados']:
                continue

            decision = AiRouteDecisionService().explain(result)
            metrics = RouteMetricsService().build(result)

            with transaction.atomic():
                # Crear la ruta
                route = Ruta.objects.create(
                    repartidor=driver,
                    aliado=Aliado.objects.filter(id=result.get('aliado_id')).first(),
                    latitud_inicio=to_decimal(result['start']['lat']),
                    longitud_inicio=to_decimal(result['start']['lng']),
                    tiempo_estimado_mins=result['duracion_total_mins'],
                    distancia_km=result['distancia_total_km'],
                    capacidad_usada_kg=result['capacidad_usada_kg'],
                    geometria=result['geometria'],
                    decision_ai={**decision, 'metrics': metrics},
                )

                # Crear las paradas
                for index, stop in enumerate(result['orden_entrega'], start=1):
                    p = stop['pedido']
                    if p.aliado_id:
                        p.save(update_fields=['aliado'])

                    RutaParada.objects.create(
                        ruta=route,
                        pedido=p,
                        orden=index,
                        latitud=to_decimal(stop['lat']),
                        longitud=to_decimal(stop['lng']),
                        distancia_desde_anterior_km=stop['distancia_desde_anterior_km'],
                        tiempo_estimado_desde_anterior_mins=stop['tiempo_estimado_desde_anterior_mins'],
                    )

                    # Asignar pedido al repartidor
                    p.repartidor = driver
                    p.estado = 'Asignado'
                    p.save(update_fields=['repartidor', 'estado'])

                # Marcar conductor como Ocupado
                driver.estado = 'Ocupado'
                driver.save(update_fields=['estado'])

            # Añadir a la lista de rutas creadas
            created_routes.append(RutaSerializer(route).data)

            # Quitar los pedidos asignados de la lista de pendientes
            assigned_ids = {p.id for p in result['pedidos_seleccionados']}
            remaining_order_ids = [pid for pid in remaining_order_ids if pid not in assigned_ids]

        return Response({
            "mensaje": f"Optimización en lote completada con éxito. Se generaron {len(created_routes)} rutas.",
            "rutas_creadas": created_routes,
            "pedidos_restantes": len(remaining_order_ids)
        }, status=status.HTTP_200_OK)

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
        with transaction.atomic():
            order_ids = list(route.paradas.values_list('pedido_id', flat=True))
            Pedido.objects.filter(id__in=order_ids).update(
                repartidor=route.repartidor,
                estado='Asignado',
            )
            route.estado_ruta = 'asignada'
            route.save(update_fields=['estado_ruta'])
            route.repartidor.estado = 'Ocupado'
            route.repartidor.save(update_fields=['estado'])

        return Response(RutaSerializer(route).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        route = self.get_object()
        next_status = request.data.get('estado_ruta')
        valid_statuses = {choice[0] for choice in Ruta._meta.get_field('estado_ruta').choices}
        if next_status not in valid_statuses:
            return Response(
                {'error': f'estado_ruta invalido. Use uno de: {sorted(valid_statuses)}'},
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

    def _serialize_optimizer_result(self, result):
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
