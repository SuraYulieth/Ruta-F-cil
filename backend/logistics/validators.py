"""
Módulo de validadores personalizados para garantizar consistencia en mensajes de error en español.
"""
from rest_framework import serializers
from decimal import InvalidOperation


class CoordinateValidator:
    """Validador para coordenadas geográficas (latitud/longitud)."""
    
    def __init__(self, field_name_es="Coordenada"):
        self.field_name_es = field_name_es
    
    def __call__(self, value):
        if value is None:
            return
        try:
            float(value)
        except (ValueError, TypeError, InvalidOperation):
            raise serializers.ValidationError(
                f"{self.field_name_es} debe ser un número válido."
            )


class LatitudeValidator:
    """Validador para latitud."""
    
    def __call__(self, value):
        if value is None:
            return
        try:
            lat = float(value)
        except (ValueError, TypeError, InvalidOperation):
            raise serializers.ValidationError(
                "La latitud debe ser un número válido."
            )
        if not (-90 <= lat <= 90):
            raise serializers.ValidationError(
                "La latitud debe estar entre -90 y 90 grados."
            )


class LongitudeValidator:
    """Validador para longitud."""
    
    def __call__(self, value):
        if value is None:
            return
        try:
            lng = float(value)
        except (ValueError, TypeError, InvalidOperation):
            raise serializers.ValidationError(
                "La longitud debe ser un número válido."
            )
        if not (-180 <= lng <= 180):
            raise serializers.ValidationError(
                "La longitud debe estar entre -180 y 180 grados."
            )


class PositiveNumberValidator:
    """Validador para números positivos."""
    
    def __init__(self, field_name_es="El valor", zero_allowed=False):
        self.field_name_es = field_name_es
        self.zero_allowed = zero_allowed
    
    def __call__(self, value):
        if value is None:
            return
        try:
            num = float(value)
        except (ValueError, TypeError, InvalidOperation):
            raise serializers.ValidationError(
                f"{self.field_name_es} debe ser un número válido."
            )
        
        min_val = 0 if self.zero_allowed else 0.01
        if num < min_val:
            if self.zero_allowed:
                raise serializers.ValidationError(
                    f"{self.field_name_es} no puede ser negativo."
                )
            else:
                raise serializers.ValidationError(
                    f"{self.field_name_es} debe ser mayor que cero."
                )


class NonNegativeNumberValidator:
    """Validador para números no negativos."""
    
    def __init__(self, field_name_es="El valor"):
        self.field_name_es = field_name_es
    
    def __call__(self, value):
        if value is None:
            return
        try:
            num = float(value)
        except (ValueError, TypeError, InvalidOperation):
            raise serializers.ValidationError(
                f"{self.field_name_es} debe ser un número válido."
            )
        if num < 0:
            raise serializers.ValidationError(
                f"{self.field_name_es} no puede ser negativo."
            )


# Mensajes de error reutilizables por tipo de campo
ERROR_MESSAGES_TEMPLATES = {
    'decimal': {
        'required': '{field} es obligatoria.',
        'invalid': '{field} debe ser un número válido.',
        'max_digits': '{field} no puede tener más de {max_digits} dígitos en total.',
        'max_decimal_places': '{field} no puede tener más de {decimal_places} decimales.',
        'max_whole_digits': '{field} tiene demasiados dígitos antes del punto decimal.',
    },
    'integer': {
        'required': '{field} es obligatoria.',
        'invalid': '{field} debe ser un número entero válido.',
    },
    'string': {
        'required': '{field} es obligatoria.',
        'blank': '{field} no puede estar vacía.',
        'max_length': '{field} no puede exceder {max_length} caracteres.',
    },
    'email': {
        'required': '{field} es obligatoria.',
        'invalid': '{field} debe ser una dirección de correo válida.',
    },
}


def get_error_messages_for_field(field_type, field_name_es, **kwargs):
    """
    Genera mensajes de error localizados al español para un campo específico.
    
    Args:
        field_type: Tipo de campo ('decimal', 'integer', 'string', 'email')
        field_name_es: Nombre del campo en español (ej: "La latitud")
        **kwargs: Argumentos adicionales para las plantillas (ej: max_digits, decimal_places)
    
    Returns:
        Diccionario con mensajes de error en español
    """
    template = ERROR_MESSAGES_TEMPLATES.get(field_type, {})
    messages = {}
    
    for key, message_template in template.items():
        try:
            messages[key] = message_template.format(field=field_name_es, **kwargs)
        except KeyError:
            messages[key] = message_template.format(field=field_name_es)
    
    return messages


# Campos decimales pre-configurados con validaciones en español
def get_latitude_field(**kwargs):
    """Retorna un DecimalField pre-configurado para latitud."""
    defaults = {
        'max_digits': 10,
        'decimal_places': 8,
        'error_messages': get_error_messages_for_field(
            'decimal',
            'La latitud',
            max_digits=10,
            decimal_places=8
        )
    }
    defaults.update(kwargs)
    return serializers.DecimalField(**defaults)


def get_longitude_field(**kwargs):
    """Retorna un DecimalField pre-configurado para longitud."""
    defaults = {
        'max_digits': 11,
        'decimal_places': 8,
        'error_messages': get_error_messages_for_field(
            'decimal',
            'La longitud',
            max_digits=11,
            decimal_places=8
        )
    }
    defaults.update(kwargs)
    return serializers.DecimalField(**defaults)


def get_weight_field(**kwargs):
    """Retorna un DecimalField pre-configurado para peso."""
    defaults = {
        'max_digits': 8,
        'decimal_places': 2,
        'error_messages': get_error_messages_for_field(
            'decimal',
            'El peso',
            max_digits=8,
            decimal_places=2
        )
    }
    defaults.update(kwargs)
    return serializers.DecimalField(**defaults)


def get_volume_field(**kwargs):
    """Retorna un DecimalField pre-configurado para volumen."""
    defaults = {
        'max_digits': 8,
        'decimal_places': 3,
        'error_messages': get_error_messages_for_field(
            'decimal',
            'El volumen',
            max_digits=8,
            decimal_places=3
        )
    }
    defaults.update(kwargs)
    return serializers.DecimalField(**defaults)


def get_capacity_field(**kwargs):
    """Retorna un DecimalField pre-configurado para capacidad."""
    defaults = {
        'max_digits': 8,
        'decimal_places': 2,
        'error_messages': get_error_messages_for_field(
            'decimal',
            'La capacidad',
            max_digits=8,
            decimal_places=2
        )
    }
    defaults.update(kwargs)
    return serializers.DecimalField(**defaults)
