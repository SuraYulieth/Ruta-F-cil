AVAILABLE_STATES = {'disponible', 'activo', 'active', 'available'}
DRIVER_ROLES = {'driver', 'repartidor'}


def normalize_text(value):
    return str(value or '').strip().lower()


def is_driver_user(user):
    return bool(user) and normalize_text(getattr(user, 'role', None)) in DRIVER_ROLES


def is_available_state(value):
    return normalize_text(value) in AVAILABLE_STATES


def is_driver_available(repartidor):
    if not repartidor or not getattr(repartidor, 'user', None):
        return False
    if not is_driver_user(repartidor.user):
        return False
    if getattr(repartidor, 'disponible', None) is not True:
        return False
    return is_available_state(getattr(repartidor.user, 'estado', None))


def _first_value(obj, field_names):
    for field_name in field_names:
        value = getattr(obj, field_name, None)
        if value not in (None, ''):
            return value
    return None


def get_driver_coordinates(repartidor):
    if not repartidor:
        return None

    lat = _first_value(repartidor, ('latitud_actual', 'latitud', 'latitude'))
    lng = _first_value(repartidor, ('longitud_actual', 'longitud', 'longitude'))

    ultima_ubicacion = getattr(repartidor, 'ultima_ubicacion', None) or {}
    if lat in (None, '') and isinstance(ultima_ubicacion, dict):
        lat = ultima_ubicacion.get('latitud') or ultima_ubicacion.get('lat') or ultima_ubicacion.get('latitude')
    if lng in (None, '') and isinstance(ultima_ubicacion, dict):
        lng = ultima_ubicacion.get('longitud') or ultima_ubicacion.get('lng') or ultima_ubicacion.get('longitude')

    if lat in (None, '') or lng in (None, ''):
        return None

    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def is_driver_outside_radius(repartidor):
    if not repartidor:
        return False

    try:
        distance = float(getattr(repartidor, 'distancia_al_centro_demanda_km', None))
        max_radius = float(getattr(repartidor, 'radio_maximo_km', None))
    except (TypeError, ValueError):
        return False

    return distance > max_radius


def driver_visibility_reason(repartidor, require_coordinates=False):
    if not repartidor:
        return 'No aparece porque no tiene perfil de repartidor.'

    user = getattr(repartidor, 'user', None)
    if not is_driver_user(user):
        return 'No aparece porque role no es driver/repartidor.'

    if getattr(repartidor, 'disponible', None) is not True:
        return 'No aparece porque esta No disponible.'

    if not is_available_state(getattr(user, 'estado', None)):
        return 'No aparece porque su estado no es disponible/activo.'

    if require_coordinates and get_driver_coordinates(repartidor) is None:
        return 'No aparece porque no tiene coordenadas.'

    if require_coordinates and is_driver_outside_radius(repartidor):
        return 'No aparece porque esta fuera del radio permitido.'

    if get_driver_coordinates(repartidor) is None:
        return 'Visible para asignacion manual; no aparece en optimizacion porque no tiene coordenadas.'

    if is_driver_outside_radius(repartidor):
        return 'Visible para asignacion manual; no aparece en optimizacion porque esta fuera del radio permitido.'

    return 'Visible para asignacion manual y optimizacion.'
