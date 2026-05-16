from rest_framework import serializers

from .models import (
    CustomUser, Aliado, Repartidor, Cliente, Pedido, PedidoProducto,
    Producto, Ruta, RutaParada
)


def validate_lat_lng(lat, lng, required=False):
    if required and (lat is None or lng is None):
        raise serializers.ValidationError('La direccion debe tener latitud y longitud validas.')
    if lat is None and lng is None:
        return
    if lat is None or lng is None:
        raise serializers.ValidationError('Latitud y longitud deben enviarse juntas.')
    if not (-90 <= float(lat) <= 90):
        raise serializers.ValidationError('Latitud fuera de rango valido.')
    if not (-180 <= float(lng) <= 180):
        raise serializers.ValidationError('Longitud fuera de rango valido.')


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
    name = serializers.CharField(source='user.nombre', read_only=True)
    latitude = serializers.DecimalField(source='latitud', max_digits=10, decimal_places=8, read_only=True)
    longitude = serializers.DecimalField(source='longitud', max_digits=11, decimal_places=8, read_only=True)

    class Meta:
        model = Aliado
        fields = ['id', 'user', 'name', 'direccion', 'latitud', 'longitud', 'latitude', 'longitude']

    def validate(self, attrs):
        direccion = attrs.get('direccion') or getattr(self.instance, 'direccion', None)
        lat = attrs.get('latitud', getattr(self.instance, 'latitud', None))
        lng = attrs.get('longitud', getattr(self.instance, 'longitud', None))
        if not direccion:
            raise serializers.ValidationError({'direccion': 'La direccion de la bodega es obligatoria.'})
        validate_lat_lng(lat, lng, required=False)
        return attrs


class RepartidorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.nombre', read_only=True)
    status = serializers.CharField(source='user.estado', read_only=True)
    latitude = serializers.DecimalField(source='latitud_actual', max_digits=10, decimal_places=8, read_only=True)
    longitude = serializers.DecimalField(source='longitud_actual', max_digits=11, decimal_places=8, read_only=True)

    class Meta:
        model = Repartidor
        fields = [
            'id', 'user', 'name', 'status', 'telefono', 'latitud_actual', 'longitud_actual',
            'latitude', 'longitude', 'capacidad_maxima_kg', 'volumen_maximo_m3'
        ]

    def validate(self, attrs):
        lat = attrs.get('latitud_actual', getattr(self.instance, 'latitud_actual', None))
        lng = attrs.get('longitud_actual', getattr(self.instance, 'longitud_actual', None))
        validate_lat_lng(lat, lng, required=False)
        capacity = attrs.get('capacidad_maxima_kg')
        if capacity is not None and capacity <= 0:
            raise serializers.ValidationError({'capacidad_maxima_kg': 'La capacidad debe ser mayor que cero.'})
        return attrs


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'

    def validate(self, attrs):
        direccion = attrs.get('direccion') or getattr(self.instance, 'direccion', None)
        lat = attrs.get('latitud', getattr(self.instance, 'latitud', None))
        lng = attrs.get('longitud', getattr(self.instance, 'longitud', None))
        if not direccion:
            raise serializers.ValidationError({'direccion': 'La direccion del cliente es obligatoria.'})
        validate_lat_lng(lat, lng, required=False)
        return attrs


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
    warehouseId = serializers.PrimaryKeyRelatedField(
        source='aliado',
        queryset=Aliado.objects.all(),
        required=False,
        allow_null=True,
    )
    warehouseName = serializers.CharField(source='aliado.user.nombre', read_only=True)
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
            'priority', 'warehouseId', 'warehouseName', 'weightKg', 'driverId',
            'fecha_creacion', 'ventana_entrega_inicio', 'ventana_entrega_fin'
        ]

    def create(self, validated_data):
        cliente_data = validated_data.pop('cliente', {})
        nombre_cliente = cliente_data.get('nombre', 'Cliente Generico')
        direccion_cliente = cliente_data.get('direccion', 'Direccion no especificada')
        latitud_cliente = cliente_data.get('latitud')
        longitud_cliente = cliente_data.get('longitud')
        validate_lat_lng(latitud_cliente, longitud_cliente, required=False)

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
            'aliado', 'tiempo_estimado_mins', 'distancia_km', 'estado_ruta',
            'capacidad_usada_kg', 'geometria', 'decision_ai', 'fecha_creacion', 'paradas'
        ]


class RouteOptimizeRequestSerializer(serializers.Serializer):
    repartidor_id = serializers.IntegerField(required=False)
    latitud_inicial = serializers.FloatField(required=False)
    longitud_inicial = serializers.FloatField(required=False)
    pedidos_candidatos = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
    )
    capacidad_maxima = serializers.FloatField(required=False)
    reglas_negocio = serializers.DictField(required=False)
