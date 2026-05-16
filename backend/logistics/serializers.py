from rest_framework import serializers
from .models import CustomUser, Aliado, Repartidor, Cliente, Pedido, Ruta

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

class PedidoSerializer(serializers.ModelSerializer):
    # Campos que coinciden con el Frontend
    customer = serializers.CharField(source='cliente.nombre', required=False)
    destination = serializers.CharField(source='cliente.direccion', required=False)
    driverId = serializers.PrimaryKeyRelatedField(
        source='repartidor', 
        queryset=CustomUser.objects.filter(role='driver'), 
        required=False, 
        allow_null=True
    )
    
    class Meta:
        model = Pedido
        fields = ['id', 'customer', 'destination', 'estado', 'driverId', 'fecha_creacion']

    def create(self, validated_data):
        # Extraer datos del cliente (que vienen en el source de DRF)
        cliente_data = validated_data.pop('cliente', {})
        nombre_cliente = cliente_data.get('nombre', 'Cliente Genérico')
        direccion_cliente = cliente_data.get('direccion', 'Dirección no especificada')

        # Buscar o crear al cliente dinámicamente
        cliente, created = Cliente.objects.get_or_create(
            nombre=nombre_cliente,
            defaults={'direccion': direccion_cliente}
        )

        # Crear el pedido
        pedido = Pedido.objects.create(cliente=cliente, **validated_data)
        return pedido

class RutaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ruta
        fields = '__all__'
