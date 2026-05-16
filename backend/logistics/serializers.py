from rest_framework import serializers

from .models import (
    CustomUser, Aliado, Repartidor, Cliente, Pedido, PedidoProducto,
    Producto, Ruta, RutaParada
)


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'role', 'nombre', 'estado', 'ubicacion', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = CustomUser(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


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


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'


class PedidoProductoSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)

    class Meta:
        model = PedidoProducto
        fields = ['id', 'producto', 'cantidad']


class PedidoSerializer(serializers.ModelSerializer):
    customer = serializers.CharField(source='cliente.nombre', required=False)
    destination = serializers.CharField(source='cliente.direccion', required=False)
    latitude = serializers.DecimalField(
        source='cliente.latitud', max_digits=10, decimal_places=8, required=False, allow_null=True
    )
    longitude = serializers.DecimalField(
        source='cliente.longitud', max_digits=11, decimal_places=8, required=False, allow_null=True
    )
    status = serializers.CharField(source='estado', required=False)
    priority = serializers.CharField(source='prioridad', required=False)
    weightKg = serializers.DecimalField(
        source='peso_total_kg', max_digits=8, decimal_places=2, required=False
    )
    driverId = serializers.PrimaryKeyRelatedField(
        source='repartidor',
        queryset=CustomUser.objects.filter(role='driver'),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Pedido
        fields = [
            'id', 'customer', 'destination', 'latitude', 'longitude', 'estado', 'status',
            'priority', 'weightKg', 'driverId', 'fecha_creacion', 'ventana_entrega_inicio',
            'ventana_entrega_fin'
        ]

    def create(self, validated_data):
        cliente_data = validated_data.pop('cliente', {})
        nombre_cliente = cliente_data.get('nombre', 'Cliente Generico')
        direccion_cliente = cliente_data.get('direccion', 'Direccion no especificada')
        latitud_cliente = cliente_data.get('latitud')
        longitud_cliente = cliente_data.get('longitud')

        cliente, created = Cliente.objects.get_or_create(
            nombre=nombre_cliente,
            defaults={
                'direccion': direccion_cliente,
                'latitud': latitud_cliente,
                'longitud': longitud_cliente,
            },
        )
        if not created:
            cliente.direccion = direccion_cliente or cliente.direccion
            if latitud_cliente is not None:
                cliente.latitud = latitud_cliente
            if longitud_cliente is not None:
                cliente.longitud = longitud_cliente
            cliente.save()

        return Pedido.objects.create(cliente=cliente, **validated_data)


class RutaParadaSerializer(serializers.ModelSerializer):
    pedido = PedidoSerializer(read_only=True)

    class Meta:
        model = RutaParada
        fields = [
            'id', 'pedido', 'orden', 'latitud', 'longitud',
            'distancia_desde_anterior_km', 'tiempo_estimado_desde_anterior_mins', 'estado'
        ]


class RutaSerializer(serializers.ModelSerializer):
    paradas = RutaParadaSerializer(many=True, read_only=True)

    class Meta:
        model = Ruta
        fields = [
            'id', 'pedido', 'repartidor', 'latitud_inicio', 'longitud_inicio',
            'tiempo_estimado_mins', 'distancia_km', 'estado_ruta',
            'capacidad_usada_kg', 'geometria', 'decision_ai', 'fecha_creacion', 'paradas'
        ]


class RouteOptimizeRequestSerializer(serializers.Serializer):
    repartidor_id = serializers.IntegerField()
    latitud_inicial = serializers.FloatField()
    longitud_inicial = serializers.FloatField()
    pedidos_candidatos = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )
    capacidad_maxima = serializers.FloatField(required=False)
    reglas_negocio = serializers.DictField(required=False)
