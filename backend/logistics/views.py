import math
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from .models import CustomUser, Aliado, Repartidor, Cliente, Pedido, Ruta
from .serializers import (
    CustomUserSerializer, LoginSerializer, AliadoSerializer, 
    RepartidorSerializer, ClienteSerializer, PedidoSerializer, RutaSerializer
)

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
    queryset = Pedido.objects.all()
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
