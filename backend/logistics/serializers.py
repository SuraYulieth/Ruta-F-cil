from rest_framework import serializers
from decimal import InvalidOperation

from .models import (
    CustomUser, Aliado, Repartidor, Cliente, Pedido, PedidoProducto,
    Producto, Ruta, RutaParada
)


def validate_lat_lng(lat, lng, required=False):
    """
    Valida que latitud y longitud sean válidas.
    - Latitud: debe estar entre -90 y 90
    - Longitud: debe estar entre -180 y 180
    """
    if required and (lat is None or lng is None):
        raise serializers.ValidationError(
            'La dirección debe tener latitud y longitud válidas.'
        )
    if lat is None and lng is None:
        return
    if lat is None or lng is None:
        raise serializers.ValidationError(
            'Latitud y longitud deben enviarse juntas.'
        )
    try:
        lat_float = float(lat)
        lng_float = float(lng)
    except (ValueError, TypeError, InvalidOperation):
        raise serializers.ValidationError(
            'Latitud y longitud deben ser números válidos.'
        )
    if not (-90 <= lat_float <= 90):
        raise serializers.ValidationError(
            'La latitud debe estar entre -90 y 90 grados.'
        )
    if not (-180 <= lng_float <= 180):
        raise serializers.ValidationError(
            'La longitud debe estar entre -180 y 180 grados.'
        )


class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        error_messages={
            'required': 'La contraseña es obligatoria.',
            'blank': 'La contraseña no puede estar vacía.',
        }
    )
    username = serializers.CharField(
        error_messages={
            'required': 'El nombre de usuario es obligatorio.',
            'blank': 'El nombre de usuario no puede estar vacío.',
        }
    )
    nombre = serializers.CharField(
        error_messages={
            'required': 'El nombre es obligatorio.',
            'blank': 'El nombre no puede estar vacío.',
        }
    )

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'role', 'nombre', 'estado', 'ubicacion', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
            'role': {
                'error_messages': {
                    'required': 'El rol es obligatorio.',
                    'blank': 'El rol no puede estar vacío.',
                }
            },
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = CustomUser(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        error_messages={
            'required': 'El nombre de usuario es obligatorio.',
            'blank': 'El nombre de usuario no puede estar vacío.',
        }
    )
    password = serializers.CharField(
        write_only=True,
        error_messages={
            'required': 'La contraseña es obligatoria.',
            'blank': 'La contraseña no puede estar vacía.',
        }
    )


class AliadoSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.nombre', read_only=True)
    latitude = serializers.DecimalField(
        source='latitud',
        max_digits=10,
        decimal_places=8,
        read_only=True,
        error_messages={
            'max_digits': 'La latitud no puede tener más de 10 dígitos en total.',
            'max_decimal_places': 'La latitud no puede tener más de 8 decimales.',
            'invalid': 'La latitud debe ser un número válido.',
        }
    )
    longitude = serializers.DecimalField(
        source='longitud',
        max_digits=11,
        decimal_places=8,
        read_only=True,
        error_messages={
            'max_digits': 'La longitud no puede tener más de 11 dígitos en total.',
            'max_decimal_places': 'La longitud no puede tener más de 8 decimales.',
            'invalid': 'La longitud debe ser un número válido.',
        }
    )
    latitud = serializers.DecimalField(
        max_digits=10,
        decimal_places=8,
        required=False,
        allow_null=True,
        error_messages={
            'max_digits': 'La latitud no puede tener más de 10 dígitos en total.',
            'max_decimal_places': 'La latitud no puede tener más de 8 decimales.',
            'invalid': 'La latitud debe ser un número válido.',
        }
    )
    longitud = serializers.DecimalField(
        max_digits=11,
        decimal_places=8,
        required=False,
        allow_null=True,
        error_messages={
            'max_digits': 'La longitud no puede tener más de 11 dígitos en total.',
            'max_decimal_places': 'La longitud no puede tener más de 8 decimales.',
            'invalid': 'La longitud debe ser un número válido.',
        }
    )
    direccion = serializers.CharField(
        error_messages={
            'required': 'La dirección es obligatoria.',
            'blank': 'La dirección no puede estar vacía.',
        }
    )

    class Meta:
        model = Aliado
        fields = ['id', 'user', 'name', 'direccion', 'latitud', 'longitud', 'latitude', 'longitude']

    def validate(self, attrs):
        direccion = attrs.get('direccion') or getattr(self.instance, 'direccion', None)
        lat = attrs.get('latitud', getattr(self.instance, 'latitud', None))
        lng = attrs.get('longitud', getattr(self.instance, 'longitud', None))
        if not direccion:
            raise serializers.ValidationError({'direccion': 'La dirección de la bodega es obligatoria.'})
        validate_lat_lng(lat, lng, required=False)
        return attrs


class RepartidorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.nombre', read_only=True)
    status = serializers.CharField(source='user.estado', read_only=True)
    latitude = serializers.DecimalField(
        source='latitud_actual',
        max_digits=10,
        decimal_places=8,
        read_only=True,
        error_messages={
            'max_digits': 'La latitud no puede tener más de 10 dígitos en total.',
            'max_decimal_places': 'La latitud no puede tener más de 8 decimales.',
            'invalid': 'La latitud debe ser un número válido.',
        }
    )
    longitude = serializers.DecimalField(
        source='longitud_actual',
        max_digits=11,
        decimal_places=8,
        read_only=True,
        error_messages={
            'max_digits': 'La longitud no puede tener más de 11 dígitos en total.',
            'max_decimal_places': 'La longitud no puede tener más de 8 decimales.',
            'invalid': 'La longitud debe ser un número válido.',
        }
    )
    latitud_actual = serializers.DecimalField(
        max_digits=10,
        decimal_places=8,
        required=False,
        allow_null=True,
        error_messages={
            'max_digits': 'La latitud no puede tener más de 10 dígitos en total.',
            'max_decimal_places': 'La latitud no puede tener más de 8 decimales.',
            'invalid': 'La latitud debe ser un número válido.',
        }
    )
    longitud_actual = serializers.DecimalField(
        max_digits=11,
        decimal_places=8,
        required=False,
        allow_null=True,
        error_messages={
            'max_digits': 'La longitud no puede tener más de 11 dígitos en total.',
            'max_decimal_places': 'La longitud no puede tener más de 8 decimales.',
            'invalid': 'La longitud debe ser un número válido.',
        }
    )
    capacidad_maxima_kg = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        error_messages={
            'required': 'La capacidad máxima en kg es obligatoria.',
            'invalid': 'La capacidad máxima debe ser un número válido.',
            'max_digits': 'La capacidad no puede tener más de 8 dígitos en total.',
            'max_decimal_places': 'La capacidad no puede tener más de 2 decimales.',
        }
    )
    volumen_maximo_m3 = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
        required=False,
        allow_null=True,
        error_messages={
            'invalid': 'El volumen máximo debe ser un número válido.',
            'max_digits': 'El volumen no puede tener más de 8 dígitos en total.',
            'max_decimal_places': 'El volumen no puede tener más de 3 decimales.',
        }
    )
    telefono = serializers.CharField(
        required=False,
        allow_blank=True,
        error_messages={
            'invalid': 'El teléfono debe ser un texto válido.',
        }
    )

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
            raise serializers.ValidationError(
                {'capacidad_maxima_kg': 'La capacidad debe ser mayor que cero kilogramos.'}
            )
        
        volume = attrs.get('volumen_maximo_m3')
        if volume is not None and volume <= 0:
            raise serializers.ValidationError(
                {'volumen_maximo_m3': 'El volumen debe ser mayor que cero metros cúbicos.'}
            )
        return attrs


class ClienteSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(
        error_messages={
            'required': 'El nombre del cliente es obligatorio.',
            'blank': 'El nombre del cliente no puede estar vacío.',
        }
    )
    direccion = serializers.CharField(
        error_messages={
            'required': 'La dirección es obligatoria.',
            'blank': 'La dirección no puede estar vacía.',
        }
    )
    latitud = serializers.DecimalField(
        max_digits=10,
        decimal_places=8,
        required=False,
        allow_null=True,
        error_messages={
            'max_digits': 'La latitud no puede tener más de 10 dígitos en total.',
            'max_decimal_places': 'La latitud no puede tener más de 8 decimales.',
            'invalid': 'La latitud debe ser un número válido.',
        }
    )
    longitud = serializers.DecimalField(
        max_digits=11,
        decimal_places=8,
        required=False,
        allow_null=True,
        error_messages={
            'max_digits': 'La longitud no puede tener más de 11 dígitos en total.',
            'max_decimal_places': 'La longitud no puede tener más de 8 decimales.',
            'invalid': 'La longitud debe ser un número válido.',
        }
    )
    correo = serializers.EmailField(
        required=False,
        allow_blank=True,
        error_messages={
            'invalid': 'El correo electrónico debe ser una dirección válida.',
        }
    )
    telefono = serializers.CharField(
        required=False,
        allow_blank=True,
        error_messages={
            'invalid': 'El teléfono debe ser un texto válido.',
        }
    )

    class Meta:
        model = Cliente
        fields = ['id', 'nombre', 'correo', 'telefono', 'direccion', 'latitud', 'longitud']

    def validate(self, attrs):
        direccion = attrs.get('direccion') or getattr(self.instance, 'direccion', None)
        lat = attrs.get('latitud', getattr(self.instance, 'latitud', None))
        lng = attrs.get('longitud', getattr(self.instance, 'longitud', None))
        if not direccion:
            raise serializers.ValidationError({'direccion': 'La dirección del cliente es obligatoria.'})
        validate_lat_lng(lat, lng, required=False)
        return attrs


class ProductoSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(
        error_messages={
            'required': 'El nombre del producto es obligatorio.',
            'blank': 'El nombre del producto no puede estar vacío.',
        }
    )
    descripcion = serializers.CharField(
        required=False,
        allow_blank=True,
        error_messages={
            'invalid': 'La descripción debe ser un texto válido.',
        }
    )
    peso_kg = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        error_messages={
            'invalid': 'El peso debe ser un número válido.',
            'max_digits': 'El peso no puede tener más de 8 dígitos en total.',
            'max_decimal_places': 'El peso no puede tener más de 2 decimales.',
        }
    )
    volumen_m3 = serializers.DecimalField(
        max_digits=8,
        decimal_places=3,
        required=False,
        allow_null=True,
        error_messages={
            'invalid': 'El volumen debe ser un número válido.',
            'max_digits': 'El volumen no puede tener más de 8 dígitos en total.',
            'max_decimal_places': 'El volumen no puede tener más de 3 decimales.',
        }
    )

    class Meta:
        model = Producto
        fields = ['id', 'nombre', 'descripcion', 'peso_kg', 'volumen_m3']

    def validate(self, attrs):
        peso = attrs.get('peso_kg')
        if peso is not None and peso < 0:
            raise serializers.ValidationError(
                {'peso_kg': 'El peso no puede ser negativo.'}
            )
        
        volumen = attrs.get('volumen_m3')
        if volumen is not None and volumen < 0:
            raise serializers.ValidationError(
                {'volumen_m3': 'El volumen no puede ser negativo.'}
            )
        return attrs


class PedidoProductoSerializer(serializers.ModelSerializer):
    producto = ProductoSerializer(read_only=True)
    cantidad = serializers.IntegerField(
        error_messages={
            'required': 'La cantidad es obligatoria.',
            'invalid': 'La cantidad debe ser un número entero válido.',
        }
    )

    class Meta:
        model = PedidoProducto
        fields = ['id', 'producto', 'cantidad']

    def validate(self, attrs):
        cantidad = attrs.get('cantidad')
        if cantidad is not None and cantidad <= 0:
            raise serializers.ValidationError(
                {'cantidad': 'La cantidad debe ser mayor que cero.'}
            )
        return attrs


class PedidoSerializer(serializers.ModelSerializer):
    customer = serializers.CharField(
        source='cliente.nombre',
        required=False,
        error_messages={
            'invalid': 'El nombre del cliente debe ser un texto válido.',
        }
    )
    destination = serializers.CharField(
        source='cliente.direccion',
        required=False,
        error_messages={
            'invalid': 'La dirección debe ser un texto válido.',
        }
    )
    latitude = serializers.DecimalField(
        source='cliente.latitud',
        max_digits=10,
        decimal_places=8,
        required=False,
        allow_null=True,
        error_messages={
            'max_digits': 'La latitud no puede tener más de 10 dígitos en total.',
            'max_decimal_places': 'La latitud no puede tener más de 8 decimales.',
            'invalid': 'La latitud debe ser un número válido.',
        }
    )
    longitude = serializers.DecimalField(
        source='cliente.longitud',
        max_digits=11,
        decimal_places=8,
        required=False,
        allow_null=True,
        error_messages={
            'max_digits': 'La longitud no puede tener más de 11 dígitos en total.',
            'max_decimal_places': 'La longitud no puede tener más de 8 decimales.',
            'invalid': 'La longitud debe ser un número válido.',
        }
    )
    status = serializers.CharField(
        source='estado',
        required=False,
        error_messages={
            'invalid': 'El estado debe ser un texto válido.',
        }
    )
    priority = serializers.CharField(
        source='prioridad',
        required=False,
        error_messages={
            'invalid': 'La prioridad debe ser un texto válido.',
        }
    )
    warehouseId = serializers.PrimaryKeyRelatedField(
        source='aliado',
        queryset=Aliado.objects.all(),
        required=False,
        allow_null=True,
        error_messages={
            'does_not_exist': 'El almacén especificado no existe.',
            'incorrect_type': 'El ID del almacén debe ser un número entero.',
        }
    )
    warehouseName = serializers.CharField(source='aliado.user.nombre', read_only=True)
    weightKg = serializers.DecimalField(
        source='peso_total_kg',
        max_digits=8,
        decimal_places=2,
        required=False,
        error_messages={
            'max_digits': 'El peso no puede tener más de 8 dígitos en total.',
            'max_decimal_places': 'El peso no puede tener más de 2 decimales.',
            'invalid': 'El peso debe ser un número válido.',
        }
    )
    driverId = serializers.PrimaryKeyRelatedField(
        source='repartidor',
        queryset=CustomUser.objects.filter(role='driver'),
        required=False,
        allow_null=True,
        error_messages={
            'does_not_exist': 'El repartidor especificado no existe.',
            'incorrect_type': 'El ID del repartidor debe ser un número entero.',
        }
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
        nombre_cliente = cliente_data.get('nombre', 'Cliente Genérico')
        direccion_cliente = cliente_data.get('direccion', 'Dirección no especificada')
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
    latitud = serializers.DecimalField(
        max_digits=10,
        decimal_places=8,
        error_messages={
            'max_digits': 'La latitud no puede tener más de 10 dígitos en total.',
            'max_decimal_places': 'La latitud no puede tener más de 8 decimales.',
            'invalid': 'La latitud debe ser un número válido.',
        }
    )
    longitud = serializers.DecimalField(
        max_digits=11,
        decimal_places=8,
        error_messages={
            'max_digits': 'La longitud no puede tener más de 11 dígitos en total.',
            'max_decimal_places': 'La longitud no puede tener más de 8 decimales.',
            'invalid': 'La longitud debe ser un número válido.',
        }
    )
    orden = serializers.IntegerField(
        error_messages={
            'invalid': 'El orden debe ser un número entero válido.',
        }
    )

    class Meta:
        model = RutaParada
        fields = [
            'id', 'pedido', 'orden', 'latitud', 'longitud',
            'distancia_desde_anterior_km', 'tiempo_estimado_desde_anterior_mins', 'estado'
        ]


class RutaSerializer(serializers.ModelSerializer):
    paradas = RutaParadaSerializer(many=True, read_only=True)
    latitud_inicio = serializers.DecimalField(
        max_digits=10,
        decimal_places=8,
        error_messages={
            'max_digits': 'La latitud no puede tener más de 10 dígitos en total.',
            'max_decimal_places': 'La latitud no puede tener más de 8 decimales.',
            'invalid': 'La latitud debe ser un número válido.',
        }
    )
    longitud_inicio = serializers.DecimalField(
        max_digits=11,
        decimal_places=8,
        error_messages={
            'max_digits': 'La longitud no puede tener más de 11 dígitos en total.',
            'max_decimal_places': 'La longitud no puede tener más de 8 decimales.',
            'invalid': 'La longitud debe ser un número válido.',
        }
    )

    class Meta:
        model = Ruta
        fields = [
            'id', 'pedido', 'repartidor', 'latitud_inicio', 'longitud_inicio',
            'aliado', 'tiempo_estimado_mins', 'distancia_km', 'estado_ruta',
            'capacidad_usada_kg', 'geometria', 'decision_ai', 'fecha_creacion', 'paradas'
        ]


class OptionalIntegerOrAutoField(serializers.Field):
    default_error_messages = {
        'invalid': 'El ID del repartidor debe ser un número entero válido o "auto".',
    }

    def to_internal_value(self, data):
        if data is None or data == '' or str(data).strip().lower() in ('auto', 'automatico'):
            return None
        try:
            return int(data)
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, value):
        return value


class RouteOptimizeRequestSerializer(serializers.Serializer):
    modo = serializers.ChoiceField(
        choices=['ruta_unica', 'multi_ruta'],
        required=False,
        default='ruta_unica',
        error_messages={
            'invalid_choice': 'El modo debe ser ruta_unica o multi_ruta.',
        }
    )
    repartidor_id = OptionalIntegerOrAutoField(
        required=False,
        allow_null=True,
    )
    latitud_inicial = serializers.FloatField(
        required=False,
        error_messages={
            'invalid': 'La latitud inicial debe ser un número válido.',
        }
    )
    longitud_inicial = serializers.FloatField(
        required=False,
        error_messages={
            'invalid': 'La longitud inicial debe ser un número válido.',
        }
    )
    pedidos_candidatos = serializers.ListField(
        child=serializers.IntegerField(
            error_messages={
                'invalid': 'Cada ID de pedido debe ser un número entero válido.',
            }
        ),
        required=False,
        allow_empty=True,
        error_messages={
            'invalid': 'Los pedidos candidatos deben ser una lista válida.',
        }
    )
    capacidad_maxima = serializers.FloatField(
        required=False,
        error_messages={
            'invalid': 'La capacidad máxima debe ser un número válido.',
        }
    )
    max_duration_mins = serializers.FloatField(
        required=False,
        error_messages={
            'invalid': 'La duración máxima debe ser un número válido.',
        }
    )
    max_area_km2 = serializers.FloatField(
        required=False,
        error_messages={
            'invalid': 'El área máxima debe ser un número válido.',
        }
    )
    max_distance_km = serializers.FloatField(
        required=False,
        error_messages={
            'invalid': 'La distancia máxima debe ser un número válido.',
        }
    )
    reglas_negocio = serializers.DictField(
        required=False,
        error_messages={
            'invalid': 'Las reglas de negocio deben ser un diccionario válido.',
        }
    )

    def validate(self, attrs):
        if attrs.get('latitud_inicial') is not None and attrs.get('longitud_inicial') is not None:
            lat = attrs.get('latitud_inicial')
            lng = attrs.get('longitud_inicial')
            if not (-90 <= lat <= 90):
                raise serializers.ValidationError(
                    {'latitud_inicial': 'La latitud debe estar entre -90 y 90 grados.'}
                )
            if not (-180 <= lng <= 180):
                raise serializers.ValidationError(
                    {'longitud_inicial': 'La longitud debe estar entre -180 y 180 grados.'}
                )
        
        if attrs.get('capacidad_maxima') is not None and attrs.get('capacidad_maxima') <= 0:
            raise serializers.ValidationError(
                {'capacidad_maxima': 'La capacidad máxima debe ser mayor que cero.'}
            )

        if attrs.get('max_duration_mins') is not None and attrs.get('max_duration_mins') <= 0:
            raise serializers.ValidationError(
                {'max_duration_mins': 'La duración máxima debe ser mayor que cero.'}
            )

        if attrs.get('max_area_km2') is not None and attrs.get('max_area_km2') <= 0:
            raise serializers.ValidationError(
                {'max_area_km2': 'El área máxima debe ser mayor que cero.'}
            )

        if attrs.get('max_distance_km') is not None and attrs.get('max_distance_km') <= 0:
            raise serializers.ValidationError(
                {'max_distance_km': 'La distancia máxima debe ser mayor que cero.'}
            )

        return attrs


class AssignPedidoRequestSerializer(serializers.Serializer):
    """
    Serializer para validar requests de asignación manual de pedidos.
    Entrada: {"repartidor_id": 3}
    """
    repartidor_id = serializers.IntegerField(
        error_messages={
            'required': 'Debe seleccionar un repartidor.',
            'invalid': 'El ID del repartidor debe ser un número entero válido.',
        }
    )

    def validate_repartidor_id(self, value):
        try:
            CustomUser.objects.get(id=value, role='driver')
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError('El repartidor seleccionado no existe.')
        return value


class RepartidorInfoSerializer(serializers.ModelSerializer):
    """
    Serializer simple para exponer información del repartidor asignado.
    Usado en respuestas de asignación.
    """
    name = serializers.CharField(source='user.nombre', read_only=True)
    status = serializers.CharField(source='user.estado', read_only=True)

    class Meta:
        model = Repartidor
        fields = ['id', 'name', 'status', 'latitud_actual', 'longitud_actual', 'capacidad_maxima_kg']
        read_only_fields = fields


class PedidoDetailResponseSerializer(serializers.ModelSerializer):
    """
    Serializer expandido para respuesta de asignación manual.
    Incluye información del repartidor asignado.
    """
    customer = serializers.CharField(source='cliente.nombre', read_only=True)
    destination = serializers.CharField(source='cliente.direccion', read_only=True)
    latitude = serializers.DecimalField(
        source='cliente.latitud', max_digits=10, decimal_places=8, read_only=True
    )
    longitude = serializers.DecimalField(
        source='cliente.longitud', max_digits=11, decimal_places=8, read_only=True
    )
    priority = serializers.CharField(source='prioridad', read_only=True)
    weightKg = serializers.DecimalField(
        source='peso_total_kg', max_digits=8, decimal_places=2, read_only=True
    )
    repartidor_info = serializers.SerializerMethodField(read_only=True)
    ruta_id = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Pedido
        fields = [
            'id', 'estado', 'customer', 'destination', 'latitude', 'longitude',
            'priority', 'weightKg', 'repartidor_info', 'ruta_id', 'fecha_creacion'
        ]
        read_only_fields = fields

    def get_repartidor_info(self, obj):
        if not obj.repartidor:
            return None

        try:
            repartidor_profile = obj.repartidor.repartidor
            serializer = RepartidorInfoSerializer(repartidor_profile)
            return serializer.data
        except Repartidor.DoesNotExist:
            return {
                'id': obj.repartidor.id,
                'name': getattr(obj.repartidor, 'nombre', None),
                'status': getattr(obj.repartidor, 'estado', None),
                'latitud_actual': None,
                'longitud_actual': None,
                'capacidad_maxima_kg': None,
            }

    def get_ruta_id(self, obj):
        first_stop = obj.paradas_ruta.order_by('ruta_id').first()
        return first_stop.ruta_id if first_stop else None


# ============================================================================
# SERIALIZERS PARA DRIVER (REPARTIDOR)
# ============================================================================

class DriverDetailSerializer(serializers.ModelSerializer):
    """Información detallada del repartidor autenticado."""
    user_id = serializers.SerializerMethodField()
    nombre = serializers.CharField(source='user.nombre', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    estado = serializers.CharField(source='user.estado', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)

    class Meta:
        model = Repartidor
        fields = [
            'id', 'user_id', 'nombre', 'email', 'username', 'estado', 'role',
            'telefono', 'latitud_actual', 'longitud_actual',
            'capacidad_maxima_kg', 'volumen_maximo_m3',
            'disponible', 'ultima_ubicacion', 'ultima_conexion'
        ]
        read_only_fields = fields

    def get_user_id(self, obj):
        return obj.user.id


class DriverLocationUpdateSerializer(serializers.Serializer):
    """Actualizar ubicación del repartidor."""
    latitud = serializers.DecimalField(max_digits=10, decimal_places=8)
    longitud = serializers.DecimalField(max_digits=11, decimal_places=8)

    def validate(self, attrs):
        lat = float(attrs.get('latitud'))
        lng = float(attrs.get('longitud'))
        if not (-90 <= lat <= 90):
            raise serializers.ValidationError({'latitud': 'Latitud debe estar entre -90 y 90'})
        if not (-180 <= lng <= 180):
            raise serializers.ValidationError({'longitud': 'Longitud debe estar entre -180 y 180'})
        return attrs


class DriverAvailabilitySerializer(serializers.Serializer):
    """Cambiar disponibilidad del repartidor."""
    disponible = serializers.BooleanField()


class DriverMyOrdersSerializer(serializers.ModelSerializer):
    """Pedidos asignados al repartidor."""
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    cliente_telefono = serializers.CharField(source='cliente.telefono', read_only=True)
    direccion = serializers.CharField(source='cliente.direccion', read_only=True)
    latitud = serializers.DecimalField(source='cliente.latitud', max_digits=10, decimal_places=8, read_only=True)
    longitud = serializers.DecimalField(source='cliente.longitud', max_digits=11, decimal_places=8, read_only=True)
    ruta_id = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = [
            'id', 'cliente_nombre', 'cliente_telefono', 'direccion', 'latitud', 'longitud',
            'estado', 'prioridad', 'peso_total_kg', 'volumen_total_m3',
            'ventana_entrega_inicio', 'ventana_entrega_fin', 'ruta_id'
        ]
        read_only_fields = fields

    def get_ruta_id(self, obj):
        """Obtener ID de la ruta asociada."""
        first_route = obj.paradas_ruta.values('ruta_id').first()
        return first_route['ruta_id'] if first_route else None


class RutaParadaDetailSerializer(serializers.ModelSerializer):
    """Detalle de una parada en la ruta."""
    cliente_nombre = serializers.SerializerMethodField()
    cliente_telefono = serializers.SerializerMethodField()
    cliente_direccion = serializers.SerializerMethodField()

    class Meta:
        model = RutaParada
        fields = [
            'id', 'pedido', 'orden', 'latitud', 'longitud',
            'distancia_desde_anterior_km', 'tiempo_estimado_desde_anterior_mins',
            'estado', 'cliente_nombre', 'cliente_telefono', 'cliente_direccion'
        ]
        read_only_fields = fields

    def get_cliente_nombre(self, obj):
        return obj.pedido.cliente.nombre

    def get_cliente_telefono(self, obj):
        return obj.pedido.cliente.telefono

    def get_cliente_direccion(self, obj):
        return obj.pedido.cliente.direccion


class DriverMyRoutesSerializer(serializers.ModelSerializer):
    """Rutas del repartidor."""
    repartidor_nombre = serializers.CharField(source='repartidor.nombre', read_only=True)
    paradas = RutaParadaDetailSerializer(many=True, read_only=True)
    total_paradas = serializers.SerializerMethodField()

    class Meta:
        model = Ruta
        fields = [
            'id', 'repartidor_nombre', 'estado_ruta',
            'latitud_inicio', 'longitud_inicio',
            'distancia_km', 'tiempo_estimado_mins',
            'capacidad_usada_kg', 'geometria',
            'paradas', 'total_paradas', 'fecha_creacion'
        ]
        read_only_fields = fields

    def get_total_paradas(self, obj):
        return obj.paradas.count()


class OrderStateChangeSerializer(serializers.Serializer):
    """Cambiar estado de un pedido."""
    estado = serializers.ChoiceField(
        choices=['Asignado', 'En ruta', 'Entregado', 'Cancelado']
    )
    comentarios = serializers.CharField(required=False, allow_blank=True)
