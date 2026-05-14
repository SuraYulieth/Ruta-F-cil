from rest_framework import serializers
from .models import Aliado, Repartidor, Cliente, Pedido, Ruta

class AliadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aliado
        fields = '__all__'

class RepartidorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repartidor
        fields = '__all__'

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'

class PedidoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.ReadOnlyField(source='cliente.nombre')
    repartidor_nombre = serializers.ReadOnlyField(source='repartidor.nombre')
    cliente_latitud = serializers.ReadOnlyField(source='cliente.latitud')
    cliente_longitud = serializers.ReadOnlyField(source='cliente.longitud')
    repartidor_latitud_actual = serializers.ReadOnlyField(source='repartidor.latitud_actual')
    repartidor_longitud_actual = serializers.ReadOnlyField(source='repartidor.longitud_actual')
    
    class Meta:
        model = Pedido
        fields = '__all__'

class RutaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ruta
        fields = '__all__'
