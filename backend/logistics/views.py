from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Aliado, Repartidor, Cliente, Pedido, Ruta
from .serializers import AliadoSerializer, RepartidorSerializer, ClienteSerializer, PedidoSerializer, RutaSerializer
import math

class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer

    @action(detail=False, methods=['post'])
    def asignar_automatico(self, request):
        """
        Algoritmo de Análisis: Greedy Matching (Vecino más cercano)
        Complejidad: O(M * N) donde M = pedidos pendientes, N = repartidores disponibles.
        """
        pedidos_pendientes = Pedido.objects.filter(estado='pendiente')
        repartidores_libres = Repartidor.objects.filter(estado='disponible')

        if not repartidores_libres.exists():
            return Response({"error": "No hay repartidores disponibles"}, status=status.HTTP_400_BAD_REQUEST)

        asignaciones = 0
        for pedido in pedidos_pendientes:
            mejor_repartidor = None
            distancia_minima = float('inf')

            # Obtener ubicación del cliente (o del aliado si ya está asignado)
            lat1 = float(pedido.cliente.latitud)
            lon1 = float(pedido.cliente.longitud)

            for repartidor in repartidores_libres:
                if repartidor.latitud_actual and repartidor.longitud_actual:
                    lat2 = float(repartidor.latitud_actual)
                    lon2 = float(repartidor.longitud_actual)
                    
                    # Distancia euclidiana (aproximación para distancias cortas)
                    dist = math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)

                    if dist < distancia_minima:
                        distancia_minima = dist
                        mejor_repartidor = repartidor

            if mejor_repartidor:
                pedido.repartidor = mejor_repartidor
                pedido.estado = 'asignado'
                pedido.save()
                
                # Opcional: Marcar repartidor como ocupado si solo puede llevar uno
                # mejor_repartidor.estado = 'ocupado'
                # mejor_repartidor.save()
                
                asignaciones += 1

        return Response({"mensaje": f"Se asignaron {asignaciones} pedidos exitosamente."}, status=status.HTTP_200_OK)

class RepartidorViewSet(viewsets.ModelViewSet):
    queryset = Repartidor.objects.all()
    serializer_class = RepartidorSerializer

class AliadoViewSet(viewsets.ModelViewSet):
    queryset = Aliado.objects.all()
    serializer_class = AliadoSerializer
